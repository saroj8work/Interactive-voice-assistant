"""
Action Planner Schemas: Plan and Step definitions for structured agent reasoning.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    step_id: str
    step_number: int
    tool_name: str
    action_description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    output_message: Optional[str] = None
    error: Optional[str] = None


class ActionPlan(BaseModel):
    plan_id: str
    goal: str
    intent: str
    confidence: float
    reasoning: str
    steps: List[PlanStep] = Field(default_factory=list)
    final_response: Optional[str] = None
    is_composite: bool = False
