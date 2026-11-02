"""
PydanticAI-powered Voice Assistant Agent (Strictly LLM-Driven).
Uses the configured LLM model for type-safe structured classification and planning.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import settings
from app.nlu.models import IntentType
from app.agent.llm_client import llm_client, LLMAgentDecision
from app.knowledge.markdown_loader import domain_knowledge
from app.tools.registry import tool_registry


@dataclass
class VoiceAgentDeps:
    """Dependencies injected into agent context."""
    notes_dir: Path = field(default_factory=lambda: settings.notes_dir)
    user_location: str = "current location"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class PlannedStepModel(BaseModel):
    step_id: str = Field(..., description="Unique step identifier, e.g. 'step_1'")
    step_number: int = Field(..., description="1-based execution order")
    tool_name: str = Field(..., description="Tool to invoke")
    action_description: str = Field(..., description="Human-readable description of this step")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the tool")
    dependencies: List[str] = Field(default_factory=list, description="IDs of steps whose output is required")


class VoiceAgentClassificationAndPlan(BaseModel):
    """Structured output schema returned by the LLM Planner Agent."""
    intent: IntentType = Field(..., description="Classified intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    reasoning: str = Field(..., description="Explanation of intent and planning choice")
    steps: List[PlannedStepModel] = Field(default_factory=list, description="Ordered action steps")
    is_composite: bool = Field(False, description="Whether command requires multiple tools")


class VoiceAgentResponse(BaseModel):
    spoken_response: str = Field(..., description="Natural language spoken response for user")
    action_summary: str = Field(..., description="Summary of actions performed")
    executed_tools: List[str] = Field(default_factory=list)


class PydanticVoiceAgent:
    """
    Strictly LLM-driven agent conforming to Pydantic schemas.
    """

    def plan_and_classify(self, command: str) -> VoiceAgentClassificationAndPlan:
        # Build prompt
        raw_markdown = ""
        if domain_knowledge.file_path.exists():
            try:
                raw_markdown = domain_knowledge.file_path.read_text(encoding="utf-8")
            except Exception:
                pass

        tools_list = tool_registry.list_tools()
        tools_desc = "\n".join(
            [f"- {t['name']}: {t['description']} (parameters: {t['parameters']})" for t in tools_list]
        )

        system_prompt = (
            "You are an expert voice command classifier and action planner.\n\n"
            "=== DOMAIN KNOWLEDGE ===\n"
            f"{raw_markdown}\n\n"
            "=== TOOLS ===\n"
            f"{tools_desc}\n"
        )

        decision: LLMAgentDecision = llm_client.call_agent(
            messages=[{"role": "user", "content": command}],
            system_prompt=system_prompt,
        )

        try:
            intent_enum = IntentType(decision.intent)
        except ValueError:
            intent_enum = IntentType.UNKNOWN

        planned_steps = [
            PlannedStepModel(
                step_id=f"step_{idx}",
                step_number=idx,
                tool_name=pt.tool_name,
                action_description=pt.action_description,
                parameters=pt.parameters,
            )
            for idx, pt in enumerate(decision.planned_tools, 1)
        ]

        return VoiceAgentClassificationAndPlan(
            intent=intent_enum,
            confidence=0.95,
            entities={},
            reasoning=decision.thought,
            steps=planned_steps,
            is_composite=len(planned_steps) > 1,
        )


pydantic_voice_agent = PydanticVoiceAgent()
