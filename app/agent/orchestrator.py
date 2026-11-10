"""
Voice Agent Orchestrator (Strictly LLM-Driven).
Coordinates audio ingestion, speech-to-text, and passes requests to the LLM Conversational Agent.
"""
from __future__ import annotations
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.audio.stt import stt_service
from app.audio.tts import tts_service
from app.agent.conversational import conversational_agent, ConversationalTurnResponse
from app.agent.llm_client import UIAction
from app.nlu.models import IntentType, IntentClassificationResult
from app.planner.schema import ActionPlan


class AgentExecutionResult(BaseModel):
    transcript: str
    classification: IntentClassificationResult
    plan: Optional[ActionPlan] = None
    executed_steps: list[Dict[str, Any]] = Field(default_factory=list)
    ui_actions: list[UIAction] = Field(default_factory=list)
    final_response: str
    audio_base64: Optional[str] = None
    execution_time_ms: float


class VoiceAgentOrchestrator:
    def __init__(self):
        self.agent = conversational_agent

    def process_command(
        self,
        text: str,
        generate_audio: bool = True,
        session_id: Optional[str] = None,
    ) -> AgentExecutionResult:
        """
        Executes a transcribed voice or text command via the LLM agent.
        """
        turn: ConversationalTurnResponse = self.agent.chat(
            user_message=text,
            session_id=session_id,
            generate_audio=generate_audio,
        )

        try:
            intent_enum = IntentType(turn.intent)
        except ValueError:
            intent_enum = IntentType.UNKNOWN

        classification = IntentClassificationResult(
            raw_text=text,
            intent=intent_enum,
            confidence=turn.confidence,
            entities={},
            matched_patterns=["llm_classification"],
        )

        return AgentExecutionResult(
            transcript=text,
            classification=classification,
            plan=turn.plan,
            executed_steps=turn.executed_tools,
            ui_actions=turn.ui_actions,
            final_response=turn.assistant_reply,
            audio_base64=turn.audio_base64,
            execution_time_ms=turn.turn_latency_ms,
        )

    def process_voice_audio(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        generate_audio: bool = True,
        session_id: Optional[str] = None,
    ) -> AgentExecutionResult:
        """
        Ingests spoken voice audio bytes, transcribes them, and routes to LLM agent.
        """
        transcript = stt_service.transcribe_audio_bytes(audio_bytes, content_type)
        return self.process_command(
            transcript,
            generate_audio=generate_audio,
            session_id=session_id,
        )


orchestrator = VoiceAgentOrchestrator()
