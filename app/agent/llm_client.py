"""
Unified LLM Client Service.
Supports Google Gemini, Groq, OpenAI, Anthropic, and Ollama through a standard interface.
"""
from __future__ import annotations
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger("voice_agent.llm")


class LLMConfigurationError(Exception):
    """Raised when the selected LLM provider lacks required credentials."""
    pass


class PlannedToolCall(BaseModel):
    tool_name: str
    action_description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class LLMAgentDecision(BaseModel):
    thought: str = Field(..., description="Internal chain of thought reasoning")
    intent: str = Field(..., description="Identified intent: weather_query, calculation_math, file_note_management, productivity_timer, system_control, web_search_knowledge, conversational_chat")
    action_required: bool = Field(..., description="True if one or more tools must be executed")
    planned_tools: List[PlannedToolCall] = Field(default_factory=list, description="Ordered tool calls to fulfill the request")
    spoken_reply: str = Field(..., description="Warm, concise spoken reply for the user")


class LLMClient:
    """
    Unified client for invoking Gemini, Groq, OpenAI, Anthropic, or Ollama.
    """

    def __init__(self):
        self._mock_responses: Optional[List[Dict[str, Any]]] = None

    def set_mock_responses(self, mock_responses: Optional[List[Dict[str, Any]]]):
        """Used in test suites to mock model output without external network requests."""
        self._mock_responses = mock_responses

    def call_agent(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
    ) -> LLMAgentDecision:
        """
        Sends the conversational context and system prompt to the configured LLM,
        requesting a structured JSON decision.
        """
        if self._mock_responses:
            data = self._mock_responses.pop(0) if self._mock_responses else {}
            return LLMAgentDecision(**data)

        provider = settings.model_provider.lower().strip()
        model_name = settings.get_effective_model_name()

        # Check credentials
        if not settings.is_configured():
            key_names = {
                "gemini": "GEMINI_API_KEY",
                "groq": "GROQ_API_KEY",
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "ollama": "OLLAMA_BASE_URL",
            }
            req_key = key_names.get(provider, "API Key")
            raise LLMConfigurationError(
                f"Model provider '{provider}' is not configured. "
                f"Please provide your {req_key} in .env or via POST /api/config/model"
            )

        # Build payload
        full_system = (
            f"{system_prompt}\n\n"
            "CRITICAL INSTRUCTION: You must respond STRICTLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "thought": "brief reasoning explaining why an action is or is not needed",\n'
            '  "intent": "weather_query | calculation_math | file_note_management | productivity_timer | system_control | web_search_knowledge | conversational_chat",\n'
            '  "action_required": true or false,\n'
            '  "planned_tools": [\n'
            '    {\n'
            '      "tool_name": "weather | calculator | system | note_manager | timer_manager | knowledge_search",\n'
            '      "action_description": "human readable explanation of this step",\n'
            '      "parameters": {"param_key": "param_value"}\n'
            "    }\n"
            "  ],\n"
            '  "spoken_reply": "spoken natural voice reply to the user"\n'
            "}"
        )

        formatted_messages = [{"role": "system", "content": full_system}]
        formatted_messages.extend(messages)

        if provider in ("gemini", "groq", "openai", "ollama"):
            return self._call_openai_compatible(provider, model_name, formatted_messages)
        elif provider == "anthropic":
            return self._call_anthropic(model_name, formatted_messages)
        else:
            raise LLMConfigurationError(f"Unsupported model provider: '{provider}'")

    def _call_openai_compatible(
        self, provider: str, model_name: str, messages: List[Dict[str, str]]
    ) -> LLMAgentDecision:
        from openai import OpenAI

        if provider == "gemini":
            client = OpenAI(
                api_key=settings.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        elif provider == "groq":
            client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        elif provider == "ollama":
            base_url = f"{settings.ollama_base_url.rstrip('/')}/v1"
            client = OpenAI(
                api_key="ollama",
                base_url=base_url,
            )
        else:  # openai
            client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw_content = response.choices[0].message.content or "{}"
        parsed = json.loads(raw_content)
        return LLMAgentDecision(**parsed)

    def _call_anthropic(
        self, model_name: str, messages: List[Dict[str, str]]
    ) -> LLMAgentDecision:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Extract system prompt
        system_content = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        user_messages = [m for m in messages if m["role"] != "system"]

        response = client.messages.create(
            model=model_name,
            max_tokens=1024,
            system=system_content,
            messages=user_messages,
            temperature=0.2,
        )

        raw_content = response.content[0].text
        # Extract JSON from block
        json_match = raw_content
        if "```json" in raw_content:
            json_match = raw_content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw_content:
            json_match = raw_content.split("```", 1)[1].split("```", 1)[0].strip()

        parsed = json.loads(json_match)
        return LLMAgentDecision(**parsed)


llm_client = LLMClient()

