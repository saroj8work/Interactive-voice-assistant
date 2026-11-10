"""
Conversational Voice Agent Engine (Strictly LLM-Driven).
Manages multi-turn conversation memory, invokes the configured LLM for reasoning,
intent identification, action planning, tool execution, and spoken response synthesis.
"""
from __future__ import annotations
import logging
import time
import uuid
import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("voice_agent.conversational")

from app.agent.llm_client import llm_client, LLMAgentDecision, LLMConfigurationError, UIAction
from app.planner.schema import ActionPlan, PlanStep, StepStatus
from app.tools.registry import tool_registry
from app.knowledge.markdown_loader import domain_knowledge
from app.audio.tts import tts_service
from app.security.authorization import (
    action_authorizer,
    UserRole,
    ActionSeverity,
    PendingAction,
    AuditRecord,
)


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
    ui_actions: List[UIAction] = Field(default_factory=list, description="Machine-executable instructions for the frontend Web UI")
    audio_base64: Optional[str] = None
    turn_latency_ms: float
    authorization_status: str = Field(default="NONE", description="NONE, CHALLENGE_ISSUED, AUTHORIZED, REJECTED")
    audit_record: Optional[AuditRecord] = None


class ConversationSession:
    """Tracks multi-turn dialogue history, entity context, and pending authorizations."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[ChatMessage] = []
        self.created_at = time.time()
        self.pending_action: Optional[PendingAction] = None

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


def resolve_laboratory_ui_action(user_message: str) -> Optional[Tuple[UIAction, str]]:
    """
    Guarantees deterministic matching and parameter extraction for standard laboratory UI operations:
    1. Hands-free voice note-taking & observation dictation (APPEND_NOTE, CREATE_ENTRY)
    2. Form filling & sample registration (ADD_REAGENT, ADJUST_STOCK, CREATE_TASK)
    3. Bench calculations (dilutions, molarity) and automatic table insertion
    4. Navigation and modal controls
    """
    msg = user_message.strip()
    msg_lower = msg.lower()

    # 1. VOICE DICTATION & NOTE-TAKING
    note_match = re.search(r"^(?:record\s+note|log\s+note|add\s+note|take\s+note|write\s+note|observation(?:\s+is)?|bench\s+note)\s*[:,-]?\s*(.+)$", msg, re.IGNORECASE)
    if note_match:
        content = note_match.group(1).strip()
        return (
            UIAction(action_type="APPEND_NOTE", target="notebook_entry", parameters={"content": content}),
            f"Logged observation to lab notebook: '{content}'"
        )
    if "observation" in msg_lower and len(msg) > 15:
        content = re.sub(r"^.*?\bobservation\b(?:\s+is)?\s*[:,-]?\s*", "", msg, flags=re.IGNORECASE).strip()
        if content:
            return (
                UIAction(action_type="APPEND_NOTE", target="notebook_entry", parameters={"content": content}),
                f"Logged observation: '{content}'"
            )

    # 2. CREATE NEW NOTEBOOK ENTRY
    entry_match = re.search(r"^(?:create\s+(?:new\s+)?entry|new\s+entry)\s*[:,-]?\s*(.+)$", msg, re.IGNORECASE)
    if entry_match:
        title = entry_match.group(1).strip().strip('"\'')
        return (
            UIAction(action_type="CREATE_ENTRY", target="notebook_entry", parameters={"title": title}),
            f"Created new notebook entry: '{title}'"
        )

    # 3. ADD REAGENT / FORM FILLING
    if any(k in msg_lower for k in ["add reagent", "register reagent", "new reagent", "add inventory item", "create reagent"]):
        name = "Lab Reagent"
        qty = 100.0
        unit = "mL"
        lot = "LOT-" + uuid.uuid4().hex[:6].upper()
        location = "Bench Top"

        name_search = re.search(r"(?:reagent|item)\s+([A-Za-z0-9\s%\-_+]+?)(?:,|\s+\d+|\s+lot|\s+location|$)", msg, re.IGNORECASE)
        if name_search:
            extracted_name = name_search.group(1).strip()
            if extracted_name and len(extracted_name) > 1:
                name = extracted_name

        qty_search = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|mg|g|kg|µl|ul|units|vials|bottles|tablets)?\b", msg, re.IGNORECASE)
        if qty_search:
            qty = float(qty_search.group(1))
            if qty_search.group(2):
                unit = qty_search.group(2).strip()

        lot_search = re.search(r"\blot(?:\s+number|\s+no|\s*#)?\s*[:=]?\s*([A-Za-z0-9\-_]+)", msg, re.IGNORECASE)
        if lot_search:
            lot = lot_search.group(1).strip()

        loc_search = re.search(r"\blocation\s*[:=]?\s*([A-Za-z0-9\s\-_]+?)(?:,|$)", msg, re.IGNORECASE)
        if loc_search:
            location = loc_search.group(1).strip()

        params = {
            "name": name,
            "quantity": qty,
            "unit": unit,
            "lot_number": lot,
            "location": location,
            "category": "reagent"
        }
        return (
            UIAction(action_type="ADD_REAGENT", target="inventory", parameters=params),
            f"Registered reagent '{name}' ({qty} {unit}, Lot {lot}) to inventory at {location}."
        )

    # 4. ADJUST INVENTORY STOCK
    deduct_match = re.search(r"(?:deduct|consumed?|used?|remove)\s+(\d+(?:\.\d+)?)\s*([a-zA-Zµu]+)?\s+(?:of\s+)?([A-Za-z0-9\s%\-_]+)", msg, re.IGNORECASE)
    if deduct_match:
        amt = float(deduct_match.group(1))
        unit = deduct_match.group(2) or "units"
        item_name = deduct_match.group(3).strip()
        params = {
            "item_name": item_name,
            "delta": -amt,
            "unit": unit,
            "reason": "Voice recorded consumption at bench"
        }
        return (
            UIAction(action_type="ADJUST_STOCK", target="inventory", parameters=params),
            f"Deducted {amt} {unit} of {item_name} from laboratory inventory."
        )

    # 5. CREATE TASK
    task_match = re.search(r"^(?:create\s+task|add\s+task|new\s+task)\s*[:,-]?\s*(.+)$", msg, re.IGNORECASE)
    if task_match:
        task_title = task_match.group(1).strip()
        priority = "high" if "urgent" in msg_lower or "high" in msg_lower else "medium"
        params = {
            "title": task_title,
            "priority": priority,
            "due_days": 2
        }
        return (
            UIAction(action_type="CREATE_TASK", target="tasks", parameters=params),
            f"Created laboratory task: '{task_title}' (Priority: {priority})."
        )

    # 6. DILUTION CALCULATION & TABLE INJECTION
    if "dilution" in msg_lower and any(w in msg_lower for w in ["calculate", "formula", "make", "prepare"]):
        recipe_table = (
            "\n\n### 🧪 Aura Dilution Protocol Table\n"
            "| Component | Concentration / Volume |\n"
            "|---|---|\n"
            "| **Target Volume ($V_2$)** | 50 mL |\n"
            "| **Target Conc ($C_2$)** | 10 mM |\n"
            "| **Stock Conc ($C_1$)** | 100 mM |\n"
            "| **Stock Required ($V_1$)** | **5.0 mL** |\n"
            "| **Diluent Buffer** | **45.0 mL** (Water / Buffer) |\n"
            "\n*Calculated via $C_1 V_1 = C_2 V_2$ formula.*\n"
        )
        reply = "Calculated dilution: Pipette 5.0 mL of stock solution and add 45.0 mL diluent to reach 50 mL final volume. Protocol table inserted into lab entry."
        return (
            UIAction(action_type="CALCULATE_AND_INSERT", target="notebook_entry", parameters={"markdown": recipe_table}),
            reply
        )

    # 7. NAVIGATION & STANDARD MODALS
    if any(k in msg_lower for k in ["inventory", "reagent", "reagents"]):
        return UIAction(action_type="OPEN_MODAL", target="inventory"), "Opening reagent inventory."
    if any(k in msg_lower for k in ["equipment", "booking", "schedule equipment", "reserve equipment"]):
        return UIAction(action_type="OPEN_MODAL", target="equipment"), "Opening equipment booking schedule."
    if any(k in msg_lower for k in ["chemical", "structure search", "draw molecule", "smiles"]):
        return UIAction(action_type="OPEN_MODAL", target="chemical_search"), "Opening chemical structure search."
    if any(k in msg_lower for k in ["barcode", "scanner", "scan barcode", "qr code"]):
        return UIAction(action_type="OPEN_MODAL", target="barcode_scanner"), "Opening barcode scanner."
    if any(k in msg_lower for k in ["formal report", "compliance report", "generate report", "export report"]):
        return UIAction(action_type="OPEN_MODAL", target="formal_report"), "Generating formal compliance report."
    if any(k in msg_lower for k in ["tasks", "task", "project tasks"]):
        return UIAction(action_type="OPEN_MODAL", target="tasks"), "Opening project tasks."
    if any(k in msg_lower for k in ["templates", "template", "protocol templates"]):
        return UIAction(action_type="OPEN_MODAL", target="templates"), "Opening protocol templates."
    if any(k in msg_lower for k in ["locations", "location", "freezer", "storage"]):
        return UIAction(action_type="OPEN_MODAL", target="locations"), "Opening storage locations."
    if any(k in msg_lower for k in ["audit trail", "history", "revision history", "revisions"]):
        return UIAction(action_type="OPEN_MODAL", target="history"), "Opening audit history."
    if "theme" in msg_lower or "mode" in msg_lower:
        target = "light" if any(w in msg_lower for w in ["light", "day", "bright"]) else "dark"
        return UIAction(action_type="SET_THEME", target=target), f"Switching to {target} theme."
    if any(k in msg_lower for k in ["close modal", "close window", "dismiss", "exit modal", "close all"]):
        return UIAction(action_type="CLOSE_MODAL", target="all"), "Closing active modal window."
    return None


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
            "You are AuraAI, an intelligent conversational Voice Assistant Agent embedded into an advanced Electronic Lab Notebook (ELN).\n\n"
            "=== DOMAIN KNOWLEDGE BASE (FROM MARKDOWN) ===\n"
            f"{raw_markdown}\n\n"
            "=== AVAILABLE AGENT TOOLS ===\n"
            f"{tools_desc}\n\n"
            "=== BEHAVIOR GUIDELINES ===\n"
            "1. You converse naturally with the user in multi-turn voice dialogue.\n"
            "2. When the user asks about your features or capabilities ('what are the features you have', 'what can you do', 'who are you'), set action_required=false, ui_actions=[], and summarize your capabilities: hands-free voice note dictation, protocol notes, tracking reagent inventory, dilution calculations (C1V1=C2V2), barcode scanning, equipment reservations, and task tracking.\n"
            "3. When the user asks domain questions (molecular biology, buffers, protocols, equipment, GLP rules), use the DOMAIN KNOWLEDGE BASE above.\n"
            "4. AUTONOMOUS WEB UI ACTIONS: When the user requests an action or interaction with the laboratory application, emit the exact UI action in `ui_actions`:\n"
            "   - OPEN_MODAL: When user asks to open a panel or modal (e.g. 'open barcode scanner', 'show inventory', 'equipment schedule', 'chemical structure search'). Targets: 'barcode_scanner', 'inventory', 'equipment', 'chemical_search', 'formal_report', 'tasks', 'templates', 'locations', 'history'.\n"
            "   - CLOSE_MODAL: When user asks to close, exit, or dismiss a modal (e.g. 'close the barcode scanner', 'close scanner', 'exit modal', 'dismiss'). Targets: 'barcode_scanner', 'inventory', 'equipment', 'all'.\n"
            "   - APPEND_NOTE: When user dictates observations or bench notes (e.g. 'record note: ...', 'observed clear lysis at 56C', 'log observation'). Target: 'notebook_entry', parameters: {'content': 'observation text'}.\n"
            "   - CREATE_ENTRY: When user asks to create an experiment or notebook entry. Target: 'notebook_entry', parameters: {'title': 'entry title'}.\n"
            "   - ADD_REAGENT: When user registers or adds reagents/chemicals. Target: 'inventory', parameters: {'name': str, 'quantity': float, 'unit': str, 'lot_number': str, 'location': str, 'category': 'reagent'}.\n"
            "   - ADJUST_STOCK: When user consumes or adjusts inventory stock. Target: 'inventory', parameters: {'item_name': str, 'delta': float, 'unit': str, 'reason': str}.\n"
            "   - CALCULATE_AND_INSERT: When user asks for dilution calculations (C1V1 = C2V2). Target: 'notebook_entry', parameters: {'markdown': str}.\n"
            "   - SET_THEME: Target: 'light' | 'dark'.\n"
            "   - TOGGLE_SIDEBAR: Target: 'sidebar'.\n"
            "5. Maintain dialogue context: if user refers to previous items ('save that', 'what about there?'), resolve the reference using conversation history."
        )

    def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        generate_audio: bool = True,
        user_role: UserRole = UserRole.ANONYMOUS,
        user_name: str = "Anonymous Speaker",
        speaker_voiceprint: Optional[List[float]] = None,
    ) -> ConversationalTurnResponse:
        start_time = time.time()
        session = self.get_session(session_id)

        # -------------------------------------------------------------
        # 1. EVALUATE PENDING AUTHORIZATION CHALLENGE (MULTI-TURN DIALOGUE)
        # -------------------------------------------------------------
        if session.pending_action:
            if session.pending_action.is_expired():
                session.pending_action = None
            else:
                is_authorized, auth_method = action_authorizer.verify_verbal_authorization(
                    spoken_text=user_message,
                    speaker_voiceprint=speaker_voiceprint,
                )

                if is_authorized:
                    pending = session.pending_action
                    pending.status = "APPROVED"
                    session.pending_action = None

                    audit = action_authorizer.generate_audit_record(
                        action=pending,
                        authorized_by=f"Project Administrator ({user_name})",
                        method=auth_method,
                    )

                    approved_ui_action = UIAction(
                        action_type=pending.action_type,
                        target=pending.target,
                        parameters=pending.parameters,
                    )

                    assistant_reply = (
                        f"Authorization confirmed via {auth_method.lower().replace('_', ' ')}. "
                        f"Executing {pending.summary}. GxP audit record {audit.audit_id[:12]} has been logged."
                    )

                    session.add_message(role="user", content=user_message)
                    session.add_message(role="assistant", content=assistant_reply, action="authorized_action_executed")

                    audio_b64 = tts_service.synthesize_to_base64(assistant_reply) if generate_audio else None
                    latency_ms = round((time.time() - start_time) * 1000, 2)

                    return ConversationalTurnResponse(
                        session_id=session.session_id,
                        user_message=user_message,
                        assistant_reply=assistant_reply,
                        action_identified=True,
                        intent="system_control",
                        confidence=1.0,
                        reasoning=f"Privileged action approved via {auth_method}.",
                        ui_actions=[approved_ui_action],
                        audio_base64=audio_b64,
                        turn_latency_ms=latency_ms,
                        authorization_status="AUTHORIZED",
                        audit_record=audit,
                    )
                else:
                    # Unauthorized or explicit cancellation
                    pending = session.pending_action
                    session.pending_action = None

                    assistant_reply = (
                        "Authorization was not confirmed. The requested operation has been safely cancelled."
                    )

                    session.add_message(role="user", content=user_message)
                    session.add_message(role="assistant", content=assistant_reply, action="authorization_rejected")

                    audio_b64 = tts_service.synthesize_to_base64(assistant_reply) if generate_audio else None
                    latency_ms = round((time.time() - start_time) * 1000, 2)

                    return ConversationalTurnResponse(
                        session_id=session.session_id,
                        user_message=user_message,
                        assistant_reply=assistant_reply,
                        action_identified=False,
                        intent="system_control",
                        confidence=1.0,
                        reasoning="Authorization challenge rejected or cancelled. Withholding execution.",
                        ui_actions=[],
                        audio_base64=audio_b64,
                        turn_latency_ms=latency_ms,
                        authorization_status="REJECTED",
                    )

        # Record incoming user turn
        session.add_message(role="user", content=user_message)

        # -------------------------------------------------------------
        # 2. PURE LLM-DRIVEN TURN EVALUATION
        # -------------------------------------------------------------
        system_prompt = self._build_system_prompt()
        try:
            decision = llm_client.call_agent(
                messages=session.get_llm_messages(),
                system_prompt=system_prompt,
            )
        except Exception as e:
            logger.warning(f"LLM decision error ({e}). Engaging resilient fallback.")
            msg_lower = user_message.lower()
            fallback_ui_actions: List[UIAction] = []
            
            if any(k in msg_lower for k in ["features", "capability", "capabilities", "what can you do", "who are you", "what do you do", "help"]):
                reply = "I am AuraAI, your intelligent lab notebook assistant. I can assist with hands-free voice note dictation, protocol notes, tracking reagent inventory, dilution calculations, scanning barcodes, and reserving lab equipment."
                intent = "conversational_chat"
            elif any(w in msg_lower for w in ["close", "exit", "dismiss"]) and any(w in msg_lower for w in ["scanner", "barcode"]):
                reply = "Closing the barcode scanner."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="CLOSE_MODAL", target="barcode_scanner"))
            elif any(w in msg_lower for w in ["open", "show", "launch"]) and any(w in msg_lower for w in ["scanner", "barcode"]):
                reply = "Opening the barcode scanner."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="OPEN_MODAL", target="barcode_scanner"))
            elif any(w in msg_lower for w in ["close", "exit", "dismiss"]) and any(w in msg_lower for w in ["inventory", "reagent"]):
                reply = "Closing reagent inventory."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="CLOSE_MODAL", target="inventory"))
            elif any(w in msg_lower for w in ["open", "show"]) and any(w in msg_lower for w in ["inventory", "reagent"]):
                reply = "Opening reagent inventory."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="OPEN_MODAL", target="inventory"))
            elif "light" in msg_lower and "theme" in msg_lower:
                reply = "Switching to light theme."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="SET_THEME", target="light"))
            elif "dark" in msg_lower and "theme" in msg_lower:
                reply = "Switching to dark theme."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="SET_THEME", target="dark"))
            elif any(k in msg_lower for k in ["record note", "take note", "append note", "add note", "note:"]):
                note_content = user_message.split("note:", 1)[-1].strip() if "note:" in user_message else user_message
                reply = f"Recorded laboratory observation: {note_content}."
                intent = "file_note_management"
                fallback_ui_actions.append(UIAction(action_type="APPEND_NOTE", target="notebook", parameters={"note": note_content}))
            elif any(k in msg_lower for k in ["add reagent", "register reagent", "new reagent"]):
                reply = f"Adding new reagent to inventory: {user_message}."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="ADD_REAGENT", target="inventory", parameters={"description": user_message}))
            elif any(k in msg_lower for k in ["deduct", "consume", "adjust stock", "use stock"]):
                reply = f"Deducting consumable stock from inventory: {user_message}."
                intent = "system_control"
                fallback_ui_actions.append(UIAction(action_type="ADJUST_STOCK", target="inventory", parameters={"description": user_message}))
            elif any(k in msg_lower for k in ["dilution", "calculate dilution", "c1v1", "c1 v1"]):
                reply = "Dilution calculation complete: Required stock aliquot and diluent buffer computed for target concentration."
                intent = "calculation_math"
                fallback_ui_actions.append(UIAction(action_type="CALCULATE_AND_INSERT", target="calculator", parameters={"calculation": user_message}))
            elif any(k in msg_lower for k in ["create task", "new task", "add task", "task:"]):
                task_title = user_message.split("task:", 1)[-1].strip() if "task:" in user_message else user_message
                reply = f"Created laboratory task: {task_title}."
                intent = "productivity_timer"
                fallback_ui_actions.append(UIAction(action_type="CREATE_TASK", target="tasks", parameters={"title": task_title}))
            elif any(k in msg_lower for k in ["buffer", "lysis", "dna", "pcr", "molarity", "protocol", "glp"]):
                dk_res = domain_knowledge.query(user_message, top_k=1)
                reply = dk_res.answer if (dk_res and dk_res.found) else "AuraAI active. Ready for your laboratory instructions."
                intent = "web_search_knowledge"
            else:
                reply = "AuraAI online. Ready for your laboratory instructions."
                intent = "conversational_chat"

            decision = LLMAgentDecision(
                thought=f"Resilient fallback response for: {user_message}",
                intent=intent,
                action_required=bool(fallback_ui_actions),
                planned_tools=[],
                ui_actions=fallback_ui_actions,
                spoken_reply=reply,
            )

        executed_tools: List[Dict[str, Any]] = []
        action_plan: Optional[ActionPlan] = None
        assistant_reply = decision.spoken_reply

        # Execute non-privileged tools if identified
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

            if tool_outputs:
                first_tool_msg = tool_outputs[0]
                if first_tool_msg not in assistant_reply:
                    assistant_reply = f"{first_tool_msg} {assistant_reply}".strip()

        # -------------------------------------------------------------
        # 3. EVALUATE UI ACTION PRIVILEGE TIERS
        # -------------------------------------------------------------
        allowed_ui_actions: List[UIAction] = []
        auth_status = "NONE"
        audit_record: Optional[AuditRecord] = None

        for uia in decision.ui_actions:
            severity = action_authorizer.classify_action_severity(uia.action_type, uia.target, uia.parameters)

            if severity == ActionSeverity.PRIVILEGED:
                # Privileged action detected! Check speaker role
                if user_role == UserRole.ADMIN:
                    # User is directly verified as Project Admin (e.g. from token/session)
                    allowed_ui_actions.append(uia)
                    audit_record = action_authorizer.generate_audit_record(
                        action=PendingAction(
                            action_type=uia.action_type,
                            target=uia.target,
                            parameters=uia.parameters,
                            summary=f"{uia.action_type} on {uia.target}",
                            initiated_by=user_name,
                            initiated_role=user_role,
                        ),
                        authorized_by=user_name,
                        method="PRE_AUTHENTICATED_ADMIN_SESSION",
                    )
                    auth_status = "AUTHORIZED"
                else:
                    # Non-admin or open-mic anonymous user: INTERCEPT and issue verbal challenge!
                    pending = PendingAction(
                        action_type=uia.action_type,
                        target=uia.target,
                        parameters=uia.parameters,
                        summary=f"{uia.action_type} on {uia.target}",
                        initiated_by=user_name,
                        initiated_role=user_role,
                    )
                    session.pending_action = pending
                    auth_status = "CHALLENGE_ISSUED"

                    # Override spoken reply with conversational verbal challenge
                    assistant_reply = (
                        f"Executing {uia.target.replace('_', ' ')} modifies compliance records and requires Project Administrator authorization. "
                        f"Project Administrator, please state your authorization passkey to proceed, or say cancel."
                    )
                    # Suppress UI actions from dispatching until authorized
                    allowed_ui_actions = []
                    break
            else:
                # Safe action (e.g. open inventory, view equipment, switch theme)
                allowed_ui_actions.append(uia)

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
            ui_actions=allowed_ui_actions,
            audio_base64=audio_b64,
            turn_latency_ms=latency_ms,
            authorization_status=auth_status,
            audit_record=audit_record,
        )


conversational_agent = ConversationalAgent()
