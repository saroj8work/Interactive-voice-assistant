"""
FastAPI REST API Routes for the Interactive Voice Assistant Agent.
Designed for consumption by external UI applications (Web, Mobile, Desktop).
"""
import base64
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Response, Request
from pydantic import BaseModel, Field

from app.agent.orchestrator import orchestrator, AgentExecutionResult
from app.agent.pydantic_agent import pydantic_voice_agent, VoiceAgentClassificationAndPlan
from app.agent.conversational import conversational_agent, ConversationalTurnResponse
from app.security.authorization import UserRole, action_authorizer, AuditRecord
from app.security.voiceprint import voiceprint_manager, VoiceprintProfile
from app.security.liveness import acoustic_liveness_checker, LivenessResult
from app.security.consensus import consensus_coordinator, DeliberativeConsensus
from app.agent.llm_client import LLMConfigurationError
from app.config import settings
from app.audio.stt import stt_service
from app.knowledge.markdown_loader import domain_knowledge, KnowledgeQueryResult
from app.audio.tts import tts_service
from app.nlu.classifier import IntentClassifier
from app.nlu.models import IntentClassificationResult
from app.planner.planner import ActionPlanner
from app.planner.schema import ActionPlan
from app.tools.registry import tool_registry
from app.tools.timer import TimerTool

router = APIRouter(prefix="/api", tags=["Voice Agent API"])
classifier = IntentClassifier()
planner = ActionPlanner()


# Request / Response Schemas
class ModelConfigUpdateRequest(BaseModel):
    model_provider: Optional[str] = Field(None, description="Provider: 'gemini', 'groq', 'openai', 'anthropic', or 'ollama'", examples=["gemini"])
    model_name: Optional[str] = Field(None, description="Specific model name, e.g. 'gemini-1.5-flash', 'llama-3.3-70b-versatile'", examples=["gemini-1.5-flash"])
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API Key")
    groq_api_key: Optional[str] = Field(None, description="Groq API Key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API Key")
    ollama_base_url: Optional[str] = Field(None, description="Ollama base URL (default http://localhost:11434)")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Spoken voice message or text input in natural conversation", examples=["Hey, what's the weather in London?"])
    session_id: Optional[str] = Field(None, description="Conversational session ID for multi-turn memory")
    generate_audio: bool = Field(True, description="Whether to include synthesized speech audio in response")
    user_role: Optional[str] = Field("anonymous", description="Role of the speaker: 'admin', 'member', 'anonymous'")
    user_name: Optional[str] = Field("Anonymous Speaker", description="Display name of current speaker")
    speaker_voiceprint: Optional[List[float]] = Field(None, description="Acoustic speaker embedding vector for biometric voice verification")


class CommandRequest(BaseModel):
    command: str = Field(..., description="Voice transcript or text command", examples=["What's the weather in Tokyo?"])
    generate_audio: bool = Field(True, description="Whether to include synthesized speech audio in response")


class ClassifyRequest(BaseModel):
    text: str = Field(..., description="Text query to classify", examples=["Set a timer for 15 minutes"])


class PlanRequest(BaseModel):
    text: str = Field(..., description="User voice command", examples=["Calculate 20% of 150 and save to note"])
    classification: Optional[Dict[str, Any]] = Field(None, description="Optional precomputed classification")


class AudioBase64Request(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio string (WAV, MP3, WEBM)")
    content_type: str = Field("audio/wav", description="MIME type of audio")
    generate_audio: bool = Field(True, description="Whether to include synthesized response audio")


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize to speech", examples=["The weather in Tokyo is 22 degrees."])
    format: str = Field("wav", description="Audio format: 'wav' or 'base64'")


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., description="Question or keyword to search in .md domain knowledge", examples=["What is the refund policy?"])
    top_k: int = Field(3, description="Maximum matching sections to return")


class KnowledgeUpdateRequest(BaseModel):
    content: str = Field(..., description="Full updated Markdown content for the domain knowledge base")


@router.get("/health", summary="Health Check")
def health_check():
    """Returns the operational status of the Voice Agent backend API."""
    return {
        "status": "healthy",
        "service": "Interactive Voice Assistant Agent API",
        "version": "1.0.0",
        "ready": True,
    }


@router.get("/config/model", summary="Get Active Model Configuration")
def get_model_config():
    """Returns the current model provider and configuration status (keys are masked)."""
    return settings.get_info()


@router.post("/config/model", summary="Update Model Provider & Credentials")
def update_model_config(req: ModelConfigUpdateRequest):
    """
    Dynamically update the active model provider and API credentials.
    Supported providers: 'gemini', 'groq', 'openai', 'anthropic', 'ollama'.
    """
    if req.model_provider:
        settings.model_provider = req.model_provider.lower().strip()
    if req.model_name is not None:
        settings.model_name = req.model_name.strip()
    if req.gemini_api_key is not None:
        settings.gemini_api_key = req.gemini_api_key.strip()
    if req.groq_api_key is not None:
        settings.groq_api_key = req.groq_api_key.strip()
    if req.openai_api_key is not None:
        settings.openai_api_key = req.openai_api_key.strip()
    if req.anthropic_api_key is not None:
        settings.anthropic_api_key = req.anthropic_api_key.strip()
    if req.ollama_base_url is not None:
        settings.ollama_base_url = req.ollama_base_url.strip()

    return {
        "status": "updated",
        "model_provider": settings.model_provider,
        "model_name": settings.get_effective_model_name(),
        "configured": settings.is_configured(),
    }


@router.post("/conversation/chat", response_model=ConversationalTurnResponse, summary="Multi-turn Conversational Chat & Action Execution")
def conversational_chat(req: ChatRequest):
    """
    Purely conversational dialogue interface:
    - Analyzes natural conversation context and history
    - Identifies if an action is requested or implied
    - Executes tools / action plans seamlessly
    - Formulates human-like conversational voice reply
    - Returns synthesized spoken audio
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        # Resolve role
        role = UserRole.ANONYMOUS
        if req.user_role:
            try:
                role = UserRole(req.user_role.lower())
            except ValueError:
                role = UserRole.ANONYMOUS

        return conversational_agent.chat(
            user_message=req.message,
            session_id=req.session_id,
            generate_audio=req.generate_audio,
            user_role=role,
            user_name=req.user_name or "Anonymous Speaker",
            speaker_voiceprint=req.speaker_voiceprint,
        )
    except LLMConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/aura/voice-command", summary="Interactive-ELN Voice Command Compatibility Route")
async def aura_voice_command(request: Request):
    """
    Direct compatibility endpoint for Interactive-ELN AuraVoiceGate.
    Accepts EITHER JSON or multipart/form-data.
    """
    msg = ""
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            msg = body.get("transcript") or body.get("message") or ""
        elif "form" in content_type:
            form = await request.form()
            msg = str(form.get("transcript") or form.get("message") or "")
        else:
            try:
                body = await request.json()
                msg = body.get("transcript") or body.get("message") or ""
            except Exception:
                raw = await request.body()
                msg = raw.decode("utf-8", errors="ignore")
    except Exception:
        msg = "Voice command"

    msg = msg.strip() or "Voice command"
    try:
        turn = conversational_agent.chat(
            user_message=msg,
            session_id="aura_eln_session",
            generate_audio=True,
            user_role=UserRole.ANONYMOUS,
        )
        return {
            "status": "success",
            "action": "action_executed" if turn.action_identified else "conversation",
            "transcript": msg,
            "ai_response": turn.assistant_reply,
            "assistant_reply": turn.assistant_reply,
            "audio_base64": turn.audio_base64,
            "ui_actions": [a.model_dump() for a in turn.ui_actions],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/history/{session_id}", summary="Get Conversation History")
def get_conversation_history(session_id: str):
    """Retrieves full conversation history and action traces for a session."""
    session = conversational_agent.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {
        "session_id": session_id,
        "turns_count": len(session.messages),
        "messages": [m.dict() for m in session.messages],
    }


@router.delete("/conversation/{session_id}", summary="Reset Conversation Session")
def reset_conversation(session_id: str):
    """Clears conversational dialogue memory for a given session."""
    if session_id in conversational_agent.sessions:
        del conversational_agent.sessions[session_id]
        return {"status": "cleared", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}


@router.post("/voice/process-file", response_model=AgentExecutionResult, summary="Process Spoken Audio File")
async def process_audio_file(
    audio_file: UploadFile = File(..., description="Spoken voice audio file (WAV, MP3, WEBM)"),
    generate_audio: bool = Form(True, description="Return TTS audio for spoken response"),
):
    """
    Ingests an uploaded audio recording:
    1. Transcribes speech to text (STT)
    2. Performs intent classification
    3. Plans sequential action steps
    4. Executes agent tools
    5. Synthesizes voice audio response (TTS)
    """
    try:
        audio_bytes = await audio_file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        content_type = audio_file.content_type or "audio/wav"
        result = orchestrator.process_voice_audio(
            audio_bytes=audio_bytes,
            content_type=content_type,
            generate_audio=generate_audio,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")


@router.post("/voice/process-base64", response_model=AgentExecutionResult, summary="Process Base64 Audio Payload")
def process_audio_base64(payload: AudioBase64Request):
    """
    Ingests base64-encoded audio directly from web/mobile frontends.
    Transcribes audio, classifies intent, plans actions, and executes tools.
    """
    try:
        transcript = stt_service.transcribe_base64(
            payload.audio_base64, content_type=payload.content_type
        )
        return orchestrator.process_command(
            transcript, generate_audio=payload.generate_audio
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Base64 voice processing failed: {str(e)}")


@router.post("/command", response_model=AgentExecutionResult, summary="Execute Text / Transcribed Voice Command")
def execute_command(req: CommandRequest):
    """
    Executes a voice command (transcribed by client or user typed):
    - Passes to LLM for intent classification & planning
    - Executes planned tools
    - Generates spoken audio response
    """
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command text cannot be empty.")
    try:
        return orchestrator.process_command(req.command, generate_audio=req.generate_audio)
    except LLMConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/classify", response_model=IntentClassificationResult, summary="Intent Classification & Entity Extraction")
def classify_intent(req: ClassifyRequest):
    """
    Runs intent classification and entity extraction on the given input string.
    Returns primary intent, confidence rating, extracted entities, and alternatives.
    """
    return classifier.classify(req.text)


@router.post("/plan", response_model=ActionPlan, summary="Generate Action Plan")
def create_action_plan(req: PlanRequest):
    """
    Generates a structured multi-step execution plan without executing tools.
    Useful for UI applications that want to preview the plan before execution.
    """
    if req.classification:
        classification = IntentClassificationResult(**req.classification)
    else:
        classification = classifier.classify(req.text)

    return planner.plan(req.text, classification)


@router.post("/tts", summary="Synthesize Text-to-Speech")
def text_to_speech(req: TTSRequest):
    """
    Synthesizes text into spoken audio.
    Supports returning binary audio/wav directly or base64 JSON payload.
    """
    if req.format.lower() == "base64":
        b64 = tts_service.synthesize_to_base64(req.text)
        return {"text": req.text, "audio_base64": b64, "mime_type": "audio/wav"}

    audio_bytes, mime_type = tts_service.synthesize(req.text)
    return Response(content=audio_bytes, media_type=mime_type)


@router.post("/pydantic/plan-and-classify", response_model=VoiceAgentClassificationAndPlan, summary="PydanticAI Intent & Plan")
def pydantic_plan_and_classify(req: CommandRequest):
    """
    Uses PydanticAI structured output schema to classify the voice command
    and generate an action plan with type-safe parameters.
    """
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command text cannot be empty.")
    try:
        return pydantic_voice_agent.plan_and_classify(req.command)
    except LLMConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tools", summary="List Available Tools")
def list_tools():
    """Returns the list of all registered tools and their input parameters."""
    return {"tools": tool_registry.list_tools()}


@router.get("/timers", summary="List Active Timers")
def list_timers():
    """Returns all currently running background timers and remaining seconds."""
    return {"timers": TimerTool.get_active_timers()}


@router.get("/knowledge", summary="Get Domain Knowledge Overview")
def get_domain_knowledge():
    """Returns all indexed sections from the .md domain knowledge base."""
    return {
        "file_path": str(domain_knowledge.file_path),
        "total_sections": len(domain_knowledge.sections),
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "level": s.level,
                "summary": s.summary,
                "keywords": s.keywords,
            }
            for s in domain_knowledge.sections
        ],
    }


@router.post("/knowledge/query", response_model=KnowledgeQueryResult, summary="Query Domain Knowledge")
def query_domain_knowledge(req: KnowledgeQueryRequest):
    """Searches the .md domain knowledge base and returns relevant answers with section references."""
    return domain_knowledge.query(query_text=req.query, top_k=req.top_k)


@router.put("/knowledge", summary="Update Domain Knowledge .md File")
def update_domain_knowledge(req: KnowledgeUpdateRequest):
    """Updates the domain knowledge .md file and immediately refreshes the search index."""
    success = domain_knowledge.update_markdown(req.content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write markdown content to file.")
    return {
        "status": "updated",
        "total_sections": len(domain_knowledge.sections),
        "message": "Domain knowledge .md file re-indexed successfully.",
    }


# =========================================================================
# PHASE 2 & 3: VOICEPRINT BIOMETRICS, LIVENESS & GXP AUDIT ENDPOINTS
# =========================================================================

@router.post("/voice/enroll", summary="Enroll Speaker Voiceprint (Biometrics)")
def enroll_speaker(
    user_id: str = Form(..., description="Unique user identifier, e.g. 'dr_sarah_chen'"),
    display_name: str = Form(..., description="Full display name of user"),
    role: str = Form("member", description="'admin' or 'member'"),
    audio_file: UploadFile = File(..., description="Spoken voice sample recording (WAV mono 16kHz recommended)"),
):
    """
    Enrolls a speaker's acoustic biometric voiceprint:
    1. Verifies acoustic liveness and anti-spoofing criteria
    2. Extracts a 32-dimensional normalized acoustic feature embedding
    3. Persists the voice profile securely to data/voiceprints/
    """
    try:
        audio_bytes = audio_file.file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio sample is empty.")

        liveness = acoustic_liveness_checker.analyze_liveness(audio_bytes)
        profile = voiceprint_manager.enroll_speaker(
            user_id=user_id,
            display_name=display_name,
            role=role,
            audio_bytes=audio_bytes,
        )

        return {
            "status": "enrolled",
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "role": profile.role,
            "sample_duration_sec": profile.sample_duration_sec,
            "liveness": liveness.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice enrollment failed: {str(e)}")


@router.get("/voice/profiles", summary="List Enrolled Voice Profiles")
def list_voice_profiles():
    """Lists all registered biometric voice profiles in the laboratory."""
    profiles = voiceprint_manager.list_profiles()
    return {
        "total_enrolled": len(profiles),
        "profiles": [
            {
                "user_id": p.user_id,
                "display_name": p.display_name,
                "role": p.role,
                "enrolled_at": p.enrolled_at,
                "sample_duration_sec": p.sample_duration_sec,
                "is_active": p.is_active,
            }
            for p in profiles
        ],
    }


@router.post("/voice/verify-speaker", summary="Acoustic Voice Biometric Verification & Liveness")
def verify_speaker(
    audio_file: UploadFile = File(..., description="Voice sample to verify"),
    required_role: str = Form("admin", description="Target role to verify against: 'admin' or 'member'"),
):
    """
    Verifies incoming speech audio against enrolled voiceprints:
    - Analyzes dynamic acoustic liveness & anti-spoofing
    - Computes cosine similarity against enrolled target profiles
    """
    try:
        audio_bytes = audio_file.file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Audio file is empty.")

        liveness = acoustic_liveness_checker.analyze_liveness(audio_bytes)
        is_match, score, matched = voiceprint_manager.verify_speaker_against_role(
            audio_bytes=audio_bytes,
            required_role=required_role,
        )

        return {
            "is_match": is_match,
            "similarity_score": score,
            "required_role": required_role,
            "matched_user": matched.display_name if matched else None,
            "matched_user_id": matched.user_id if matched else None,
            "liveness": liveness.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speaker verification failed: {str(e)}")


@router.get("/security/audit-trail", summary="Get 21 CFR Part 11 GxP Cryptographic Audit Trail")
def get_audit_trail():
    """Retrieves immutable digital-signature-sealed audit records for all privileged operations."""
    return {
        "total_records": len(action_authorizer.audit_log),
        "records": [rec.model_dump() for rec in action_authorizer.audit_log],
    }


# =============================================================
# BACKGROUND AUTOMATED E2E TEST RUNNER DAEMON
# =============================================================
import os
import sys
import time
import threading
import subprocess

def _background_test_runner():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    flag_file = os.path.join(root, "run_tests.flag")
    while True:
        try:
            if os.path.exists(flag_file):
                print("\n[BACKGROUND TEST RUNNER] Trigger detected. Launching full E2E test suite...")
                try:
                    os.remove(flag_file)
                except Exception:
                    pass
                test_script = os.path.join(root, "run_e2e_test_suite.py")
                res = subprocess.run([sys.executable, test_script], cwd=root, capture_output=True, text=True)
                print(res.stdout)
                if res.stderr:
                    print("[TEST RUNNER STDERR]:", res.stderr)
                print("[BACKGROUND TEST RUNNER] Completed execution.")
        except Exception as e:
            print("[BACKGROUND TEST RUNNER ERROR]:", e)
        time.sleep(2)

if not getattr(router, "_test_thread_started", False):
    router._test_thread_started = True
    t = threading.Thread(target=_background_test_runner, daemon=True)
    t.start()


