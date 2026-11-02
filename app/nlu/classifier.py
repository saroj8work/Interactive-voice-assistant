"""
Intent Classifier and Entity Extraction Engine.
Implements pattern-based and semantic intent recognition inspired by open-source
standards (Snips NLU, Rasa NLU, Home Assistant Assist).
"""
import re
from typing import Dict, Any, List, Tuple
from app.nlu.models import IntentType, IntentClassificationResult


class IntentClassifier:
    """
    Classifies voice transcripts into structured intents and extracts entities.
    """

    def __init__(self):
        self._init_patterns()

    def _init_patterns(self):
        # Intent patterns with entity extraction groups
        self.intent_rules: Dict[IntentType, List[Dict[str, Any]]] = {
            IntentType.WEATHER_QUERY: [
                {
                    "regex": re.compile(
                        r"(?:what(?:'s| is) the weather(?: like)? in|how is the weather in|weather forecast for|weather in)\s+(?P<location>[\w\s,]+)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                },
                {
                    "regex": re.compile(
                        r"(?:what(?:'s| is) the temperature in|forecast for)\s+(?P<location>[\w\s,]+)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.92,
                },
                {
                    "regex": re.compile(
                        r"\b(?:weather|temperature|forecast|rain|sunny|humidity)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.75,
                },
            ],
            IntentType.PRODUCTIVITY_TIMER: [
                {
                    "regex": re.compile(
                        r"(?:set|start|create)(?:\s+a)?\s+timer\s+(?:for\s+)?(?P<duration>\d+)\s*(?P<unit>seconds?|secs?|minutes?|mins?|hours?|hrs?)(?:\s+(?:for|to|called)\s+(?P<label>[\w\s]+))?",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.98,
                },
                {
                    "regex": re.compile(
                        r"(?:remind me to|set a reminder to)\s+(?P<reminder_text>[\w\s]+?)(?:\s+in\s+(?P<duration>\d+)\s*(?P<unit>seconds?|secs?|minutes?|mins?|hours?|hrs?))?$",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                },
                {
                    "regex": re.compile(
                        r"\b(?:timer|stopwatch|countdown|remind|reminder|alarm)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.75,
                },
            ],
            IntentType.FILE_NOTE_MANAGEMENT: [
                {
                    "regex": re.compile(
                        r"(?:take|create|make|write|save|add)(?:\s+a)?\s+note\s*(?:titled\s+(?P<title>[\w\s\-]+?))?(?:\s*:\s*|\s+that\s+|\s+saying\s+)(?P<content>.+)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                },
                {
                    "regex": re.compile(
                        r"(?:take|write|make|create|save)(?:\s+a)?\s+note\s+(?P<content>.+)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.90,
                },
                {
                    "regex": re.compile(
                        r"(?:show|list|read|get|display)\s+(?:all\s+)?(?:my\s+)?notes",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                    "default_entities": {"action": "list"},
                },
                {
                    "regex": re.compile(
                        r"\b(?:note|memo|scratchpad|save note|list notes)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.70,
                },
            ],
            IntentType.CALCULATION_MATH: [
                {
                    "regex": re.compile(
                        r"(?:calculate|compute|solve|what is|evaluate)\s+(?P<expression>[\d\.\s\+\-\*\/\^\(\)\%\$\,]+|.+percent\s+of\s+.+)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                },
                {
                    "regex": re.compile(
                        r"^(?:what(?:'s| is)\s+)?(?P<expression>[\d\.\s\+\-\*\/\(\)]+[\+\-\*\/][\d\.\s\+\-\*\/\(\)]+)$",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                },
                {
                    "regex": re.compile(
                        r"(?P<percent>\d+(?:\.\d+)?)\s*%\s*(?:of|tip on)\s*(?P<total>\$?\d+(?:\.\d+)?)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.92,
                },
                {
                    "regex": re.compile(
                        r"\b(?:calculate|add|multiply|divide|subtract|square root|percentage)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.75,
                },
            ],
            IntentType.SYSTEM_CONTROL: [
                {
                    "regex": re.compile(
                        r"(?:what(?:'s| is) the\s+)?(?:current\s+)?(?:time|date|day)(?:\s+today)?",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                    "default_entities": {"query": "datetime"},
                },
                {
                    "regex": re.compile(
                        r"(?:system status|system health|cpu usage|memory usage|ram usage|disk space|system info|check system)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                    "default_entities": {"query": "system_stats"},
                },
                {
                    "regex": re.compile(
                        r"(?:open|launch|start)\s+(?P<app_name>notepad|calculator|browser|terminal|cmd|explorer)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                },
            ],
            IntentType.WEB_SEARCH_KNOWLEDGE: [
                {
                    "regex": re.compile(
                        r"(?:search(?: for)?|google|lookup|look up|who is|who was|what is|define)\s+(?P<query>.+)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.85,
                },
                {
                    "regex": re.compile(
                        r"\b(?:search|lookup|find out about|tell me about|who is|what is)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.70,
                },
            ],
            IntentType.CONVERSATIONAL_CHAT: [
                {
                    "regex": re.compile(
                        r"^(?:hello|hi|hey|good morning|good afternoon|good evening|greetings)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.98,
                    "default_entities": {"type": "greeting"},
                },
                {
                    "regex": re.compile(
                        r"(?:who are you|what can you do|help me|what are your capabilities|features)",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                    "default_entities": {"type": "help"},
                },
                {
                    "regex": re.compile(
                        r"^(?:bye|goodbye|see you|exit|quit|stop)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                    "default_entities": {"type": "farewell"},
                },
                {
                    "regex": re.compile(
                        r"^(?:thank you|thanks|thanks a lot)\b",
                        re.IGNORECASE,
                    ),
                    "confidence": 0.95,
                    "default_entities": {"type": "gratitude"},
                },
            ],
        }

    def classify(self, text: str) -> IntentClassificationResult:
        """
        Classify input text into an intent, extract parameters and confidence.
        """
        clean_text = text.strip()
        if not clean_text:
            return IntentClassificationResult(
                raw_text=text,
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                matched_patterns=[],
            )

        scored_candidates: List[Tuple[IntentType, float, Dict[str, Any], str]] = []

        for intent, rules in self.intent_rules.items():
            for rule in rules:
                pattern = rule["regex"]
                match = pattern.search(clean_text)
                if match:
                    entities = dict(rule.get("default_entities", {}))
                    # Extract named groups
                    group_dict = match.groupdict()
                    for k, v in group_dict.items():
                        if v is not None:
                            entities[k] = v.strip()

                    # Additional entity post-processing
                    self._clean_entities(intent, entities, clean_text)

                    confidence = rule["confidence"]
                    # If query is an exact match or closely spans whole text, boost confidence
                    span_len = match.end() - match.start()
                    coverage = span_len / max(len(clean_text), 1)
                    final_confidence = min(1.0, confidence * (0.8 + 0.2 * coverage))

                    scored_candidates.append(
                        (intent, round(final_confidence, 2), entities, pattern.pattern)
                    )

        if not scored_candidates:
            # Fallback keyword scan
            fallback_intent, fb_conf, fb_entities = self._keyword_fallback(clean_text)
            return IntentClassificationResult(
                raw_text=text,
                intent=fallback_intent,
                confidence=fb_conf,
                entities=fb_entities,
                matched_patterns=["keyword_fallback"],
            )

        # Sort candidates by confidence descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_intent, top_conf, top_entities, top_pattern = scored_candidates[0]

        secondary = [
            {"intent": item[0].value, "confidence": item[1]}
            for item in scored_candidates[1:4]
            if item[0] != top_intent
        ]

        return IntentClassificationResult(
            raw_text=text,
            intent=top_intent,
            confidence=top_conf,
            entities=top_entities,
            matched_patterns=[top_pattern],
            secondary_intents=secondary,
        )

    def _clean_entities(self, intent: IntentType, entities: Dict[str, Any], text: str):
        """Entity post-processing and normalization."""
        if intent == IntentType.PRODUCTIVITY_TIMER:
            if "duration" in entities:
                try:
                    entities["duration"] = int(entities["duration"])
                except ValueError:
                    entities["duration"] = 1
            if "unit" in entities:
                u = entities["unit"].lower()
                if "sec" in u:
                    entities["unit"] = "seconds"
                elif "min" in u:
                    entities["unit"] = "minutes"
                elif "hour" in u or "hr" in u:
                    entities["unit"] = "hours"

        elif intent == IntentType.CALCULATION_MATH:
            if "percent" in entities and "total" in entities:
                tot_str = str(entities["total"]).replace("$", "").strip()
                try:
                    p = float(entities["percent"])
                    t = float(tot_str)
                    entities["expression"] = f"({p} / 100) * {t}"
                except ValueError:
                    pass

        elif intent == IntentType.WEATHER_QUERY:
            if "location" in entities:
                entities["location"] = entities["location"].rstrip("?.,!").strip()
            else:
                # Default location if not mentioned
                entities["location"] = "current location"

    def _keyword_fallback(self, text: str) -> Tuple[IntentType, float, Dict[str, Any]]:
        """Fallback heuristics for unclassified inputs."""
        lower = text.lower()
        if any(w in lower for w in ["help", "who", "hi", "hello"]):
            return IntentType.CONVERSATIONAL_CHAT, 0.60, {"type": "general"}
        if any(w in lower for w in ["calculate", "math", "+", "-", "*", "/"]):
            return IntentType.CALCULATION_MATH, 0.55, {"expression": text}
        if any(w in lower for w in ["time", "status", "system", "date"]):
            return IntentType.SYSTEM_CONTROL, 0.55, {"query": "general"}
        if any(w in lower for w in ["search", "find", "google", "explain"]):
            return IntentType.WEB_SEARCH_KNOWLEDGE, 0.55, {"query": text}

        # Catch-all
        return IntentType.UNKNOWN, 0.20, {"raw": text}
