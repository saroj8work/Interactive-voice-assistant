"""
NLU Data Models: Intent definitions, confidence scoring, and extracted entities.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    WEATHER_QUERY = "weather_query"
    SYSTEM_CONTROL = "system_control"
    PRODUCTIVITY_TIMER = "productivity_timer"
    FILE_NOTE_MANAGEMENT = "file_note_management"
    CALCULATION_MATH = "calculation_math"
    WEB_SEARCH_KNOWLEDGE = "web_search_knowledge"
    CONVERSATIONAL_CHAT = "conversational_chat"
    UNKNOWN = "unknown"


class ExtractedEntity(BaseModel):
    name: str
    value: Any
    confidence: float = 1.0


class IntentClassificationResult(BaseModel):
    raw_text: str
    intent: IntentType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(default_factory=dict)
    matched_patterns: List[str] = Field(default_factory=list)
    secondary_intents: List[Dict[str, Any]] = Field(default_factory=list)
