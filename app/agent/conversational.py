"""
Conversational Voice Agent Engine (Strictly LLM-Driven).
Manages multi-turn conversation memory, invokes the configured LLM for reasoning,
intent identification, action planning, tool execution, and spoken response synthesis.
"""
from __future__ import annotations
import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.agent.llm_client import llm_client, LLMAgentDecision, LLMConfigurationError
from app.planner.schema import ActionPlan, PlanStep, StepStatus
from app.tools.registry import tool_registry
from app.knowledge.markdown_loader import domain_knowledge
from app.audio.tts import tts_service


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'tool'")
    content: str
    timestamp: float = Field(default_factory=time.time)
    action_performed: Optional[str] = None
    tool_data: Optional[Dict[str, Any]] = None


class ConversationalTurnResponse(BaseModel):
    session_id: str
    user_message: str
    assistant_reply: str
    action_identified: bool
    intent: str
    confidence: float = 1.0
    reasoning: Optional[str] = None
    plan: Optional[ActionPlan] = None
    executed_tools: List[Dict[str, Any]] = Field(default_factory=list)
    audio_base64: Optional[str] = None
    turn_latency_ms: float


class ConversationSession:
    """Tracks multi-turn dialogue history and entity context."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[ChatMessage] = []
        self.created_at = time.time()

    def add_message(
        self,
        role: str,
        content: str,
        action: Optional[str] = None,
        tool_data: Optional[Dict[str, Any]] = None,
    ):
        self.messages.append(
            ChatMessage(
                role=role,
                content=content,
                action_performed=action,
                tool_data=tool_data,
            )
        )
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]

    def get_llm_messages(self) -> List[Dict[str, str]]:
        """Formats conversation turns into OpenAI/Anthropic message structures."""
        return [{"role": m.role, "content": m.content} for m in self.messages]


class ConversationalAgent:
    """
    Purely LLM-driven voice assistant agent.
    """

    def __init__(self):
        self.tools = tool_registry
        self.sessions: Dict[str, ConversationSession] = {}

    def get_session(self, session_id: Optional[str] = None) -> ConversationSession:
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:8]}"
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSession(session_id)
        return self.sessions[session_id]

    def _build_system_prompt(self) -> str:
        # Ingest domain knowledge from markdown file
        raw_markdown = ""
        if domain_knowledge.file_path.exists():
            try:
                raw_markdown = domain_knowledge.file_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Tools catalog
        tools_list = self.tools.list_tools()
        tools_desc = "\n".join(
            [f"- {t['name']}: {t['description']} (parameters: {t['parameters']})" for t in tools_list]
        )

        return (
            "You are an intelligent, friendly conversational Voice Assistant Agent.\n\n"
            "=== DOMAIN KNOWLEDGE BASE (FROM MARKDOWN) ===\n"
            f"{raw_markdown}\n\n"
            "=== AVAILABLE AGENT TOOLS ===\n"
            f"{tools_desc}\n\n"
            "=== BEHAVIOR GUIDELINES ===\n"
            "1. You converse naturally with the user in multi-turn voice dialogue.\n"
            "2. When the user asks casual questions (greetings, chit-chat, who you are), set action_required=false and give a friendly reply.\n"
            "3. When the user asks domain questions (support hours, refund policy, rules), use the DOMAIN KNOWLEDGE BASE above.\n"
            "4. When the user's speech implies or requests an action (checking weather, calculating math, setting timers, managing notes, checking system), set action_required=true and specify the tool(s) in planned_tools.\n"
            "5. Maintain dialogue context: if user refers to previous items ('save that', 'what about there?'), resolve the reference using conversation history."
        )

    def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        generate_audio: bool = True,
    ) -> ConversationalTurnResponse:
        start_time = time.time()
        session = self.get_session(session_id)

        # Record incoming user turn
        session.add_message(role="user", content=user_message)

        # 1. Build system prompt with domain knowledge and tools
        system_prompt = self._build_system_prompt()

        # 2. Call the LLM with conversational context
        decision: LLMAgentDecision = llm_client.call_agent(
            messages=session.get_llm_messages(),
            system_prompt=system_prompt,
        )

        executed_tools: List[Dict[str, Any]] = []
        action_plan: Optional[ActionPlan] = None
        assistant_reply = decision.spoken_reply

        # 3. Execute tools if the LLM identified actions
        if decision.action_required and decision.planned_tools:
            plan_steps: List[PlanStep] = []
            tool_outputs: List[str] = []

            for idx, pt in enumerate(decision.planned_tools, 1):
                step_id = f"step_{idx}"
                step = PlanStep(
                    step_id=step_id,
                    step_number=idx,
                    tool_name=pt.tool_name,
                    action_description=pt.action_description,
                    parameters=pt.parameters,
                    status=StepStatus.IN_PROGRESS,
                )

                tool_res = self.tools.execute_tool(pt.tool_name, pt.parameters)
                if tool_res.success:
                    step.status = StepStatus.COMPLETED
                    step.result = tool_res.data
                    step.output_message = tool_res.message
                    if tool_res.message:
                        tool_outputs.append(tool_res.message)
                else:
                    step.status = StepStatus.FAILED
                    step.error = tool_res.error
                    step.output_message = tool_res.message
                    if tool_res.message:
                        tool_outputs.append(tool_res.message)

                executed_tools.append({
                    "tool": pt.tool_name,
                    "description": pt.action_description,
                    "status": step.status.value,
                    "message": step.output_message,
                    "data": step.result,
                })
                plan_steps.append(step)

            action_plan = ActionPlan(
                plan_id=f"plan_{uuid.uuid4().hex[:8]}",
                goal=user_message,
                intent=decision.intent,
                confidence=0.95,
                reasoning=decision.thought,
                steps=plan_steps,
                final_response=" ".join(tool_outputs),
                is_composite=len(plan_steps) > 1,
            )

            # If tool returned factual content not already in spoken reply, blend it cleanly
            if tool_outputs:
                first_tool_msg = tool_outputs[0]
                if first_tool_msg not in assistant_reply:
                    assistant_reply = f"{first_tool_msg} {assistant_reply}".strip()

        # Record assistant reply in dialogue history
        session.add_message(
            role="assistant",
            content=assistant_reply,
            action=decision.intent if decision.action_required else None,
            tool_data=executed_tools[0] if executed_tools else None,
        )

        # Synthesize Voice Audio
        audio_b64 = None
        if generate_audio:
            try:
                audio_b64 = tts_service.synthesize_to_base64(assistant_reply)
            except Exception:
                pass

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return ConversationalTurnResponse(
            session_id=session.session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            action_identified=decision.action_required,
            intent=decision.intent,
            confidence=0.95,
            reasoning=decision.thought,
            plan=action_plan,
            executed_tools=executed_tools,
            audio_base64=audio_b64,
            turn_latency_ms=latency_ms,
        )


conversational_agent = ConversationalAgent()
