"""
Action Planner Engine.
Generates structured multi-step execution plans from classified voice commands,
inspired by open-source ReAct and Plan-and-Solve agent patterns.
"""
import uuid
import re
from typing import List, Dict, Any, Optional
from app.nlu.models import IntentType, IntentClassificationResult
from app.planner.schema import ActionPlan, PlanStep, StepStatus


class ActionPlanner:
    """
    Deconstructs classified voice commands into sequential executable steps.
    """

    def plan(
        self,
        text: str,
        classification: IntentClassificationResult,
    ) -> ActionPlan:
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        intent = classification.intent
        entities = classification.entities
        confidence = classification.confidence

        steps: List[PlanStep] = []
        reasoning = ""
        is_composite = False

        # Check for composite commands (e.g. "and", "then", "also")
        if self._is_composite_command(text):
            composite_steps = self._plan_composite(text, classification)
            if composite_steps:
                steps = composite_steps
                is_composite = True
                reasoning = (
                    "Detected multi-intent composite command. Created sequential multi-step plan."
                )

        if not steps:
            # Single intent planning
            steps, reasoning = self._plan_single_intent(text, classification)

        return ActionPlan(
            plan_id=plan_id,
            goal=text,
            intent=intent.value,
            confidence=confidence,
            reasoning=reasoning,
            steps=steps,
            is_composite=is_composite,
        )

    def _is_composite_command(self, text: str) -> bool:
        lower = text.lower()
        # Look for conjunctions connecting two actionable clauses
        markers = [" and then ", " and also ", " and note ", " and save ", " and tell me "]
        return any(m in lower for m in markers)

    def _plan_composite(
        self, text: str, classification: IntentClassificationResult
    ) -> Optional[List[PlanStep]]:
        steps: List[PlanStep] = []
        lower = text.lower()

        # Pattern: calculate X and note/save it
        if "calculate" in lower and ("note" in lower or "save" in lower):
            # Extract calculation portion
            calc_match = re.search(
                r"(?:calculate|compute|what is)\s+(.+?)(?:\s+and\s+(?:note|save).*)",
                text,
                re.IGNORECASE,
            )
            calc_expr = calc_match.group(1).strip() if calc_match else "10 * 2"

            # Extract note title/label
            note_match = re.search(
                r"(?:as|titled|called)\s+([\w\s]+)", text, re.IGNORECASE
            )
            title = note_match.group(1).strip() if note_match else "Calculated Expense"

            steps.append(
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    tool_name="calculator",
                    action_description=f"Evaluate mathematical expression: {calc_expr}",
                    parameters={"expression": calc_expr},
                )
            )
            steps.append(
                PlanStep(
                    step_id="step_2",
                    step_number=2,
                    tool_name="note_manager",
                    action_description=f"Save result to note titled '{title}'",
                    parameters={"action": "create", "title": title, "content": "Pending calculation result"},
                    dependencies=["step_1"],
                )
            )
            return steps

        # Pattern: timer + system stats
        if "timer" in lower and ("status" in lower or "stats" in lower or "time" in lower):
            steps.append(
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    tool_name="timer_manager",
                    action_description="Start countdown timer",
                    parameters=classification.entities,
                )
            )
            steps.append(
                PlanStep(
                    step_id="step_2",
                    step_number=2,
                    tool_name="system",
                    action_description="Check system status / date time",
                    parameters={"action": "stats"},
                )
            )
            return steps

        return None

    def _plan_single_intent(
        self, text: str, classification: IntentClassificationResult
    ) -> (List[PlanStep], str):
        intent = classification.intent
        entities = classification.entities

        if intent == IntentType.WEATHER_QUERY:
            loc = entities.get("location", "current location")
            return [
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    tool_name="weather",
                    action_description=f"Fetch weather forecast for '{loc}'",
                    parameters={"location": loc},
                )
            ], f"User requested weather information for '{loc}'. Routing to Open-Meteo weather tool."

        elif intent == IntentType.PRODUCTIVITY_TIMER:
            duration = entities.get("duration", 1)
            unit = entities.get("unit", "minutes")
            label = entities.get("label", entities.get("reminder_text", "Timer"))
            return [
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    tool_name="timer_manager",
                    action_description=f"Schedule timer for {duration} {unit} ({label})",
                    parameters={"duration": duration, "unit": unit, "label": label},
                )
            ], f"User requested setting a timer for {duration} {unit}."

        elif intent == IntentType.FILE_NOTE_MANAGEMENT:
            action = entities.get("action", "create")
            if action == "list":
                return [
                    PlanStep(
                        step_id="step_1",
                        step_number=1,
                        tool_name="note_manager",
                        action_description="Retrieve and list recent saved notes",
                        parameters={"action": "list"},
                    )
                ], "User requested to list notes from storage."
            else:
                content = entities.get("content", text)
                title = entities.get("title", "")
                return [
                    PlanStep(
                        step_id="step_1",
                        step_number=1,
                        tool_name="note_manager",
                        action_description="Save note to local storage",
                        parameters={"action": "create", "content": content, "title": title},
                    )
                ], "User requested to record a new note."

        elif intent == IntentType.CALCULATION_MATH:
            expr = entities.get("expression", text)
            # Remove command keywords if still in expression
            clean_expr = re.sub(
                r"^(?:calculate|compute|what is|evaluate)\s+", "", expr, flags=re.I
            ).strip()
            return [
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    tool_name="calculator",
                    action_description=f"Safely evaluate math expression: {clean_expr}",
                    parameters={"expression": clean_expr},
                )
            ], f"User requested mathematical calculation for '{clean_expr}'."

        elif intent == IntentType.SYSTEM_CONTROL:
            query = entities.get("query", "datetime")
            app_name = entities.get("app_name", "")
            if app_name:
                return [
                    PlanStep(
                        step_id="step_1",
                        step_number=1,
                        tool_name="system",
                        action_description=f"Launch desktop application: {app_name}",
                        parameters={"action": "launch_app", "app_name": app_name},
                    )
                ], f"User requested launching {app_name}."
            else:
                return [
                    PlanStep(
                        step_id="step_1",
                        step_number=1,
                        tool_name="system",
                        action_description=f"Query system info ({query})",
                        parameters={"action": query},
                    )
                ], f"User requested system control or status: {query}."

        elif intent == IntentType.WEB_SEARCH_KNOWLEDGE:
            query = entities.get("query", text)
            return [
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    tool_name="knowledge_search",
                    action_description=f"Search knowledge base for '{query}'",
                    parameters={"query": query},
                )
            ], f"User requested knowledge lookup for '{query}'."

        elif intent == IntentType.CONVERSATIONAL_CHAT:
            chat_type = entities.get("type", "greeting")
            if chat_type == "help":
                msg = (
                    "I am your Interactive Voice Assistant Agent! I can check weather, "
                    "calculate math, set timers, take notes, report system health, and answer questions. "
                    "Just speak your command or click any example!"
                )
            elif chat_type == "greeting":
                msg = "Hello! I am ready to assist you. What can I do for you today?"
            elif chat_type == "farewell":
                msg = "Goodbye! Let me know whenever you need assistance."
            else:
                msg = "You are very welcome! Let me know if you need anything else."

            return [
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    tool_name="conversational",
                    action_description="Generate natural language conversational response",
                    parameters={"response_text": msg},
                )
            ], f"Conversational chat recognized ({chat_type})."

        # Unknown intent fallback
        return [
            PlanStep(
                step_id="step_1",
                step_number=1,
                tool_name="knowledge_search",
                action_description=f"Attempt knowledge lookup for query: '{text}'",
                parameters={"query": text},
            )
        ], "Intent not definitively identified. Delegating to knowledge search."
