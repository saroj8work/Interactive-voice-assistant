"""
Unit tests for Intent Classifier and Entity Extraction.
"""
from app.nlu.classifier import IntentClassifier
from app.nlu.models import IntentType


def test_weather_classification():
    classifier = IntentClassifier()
    result = classifier.classify("What is the weather in Tokyo?")
    assert result.intent == IntentType.WEATHER_QUERY
    assert result.confidence >= 0.75
    assert result.entities.get("location").lower() == "tokyo"


def test_timer_classification():
    classifier = IntentClassifier()
    result = classifier.classify("Set a timer for 5 minutes")
    assert result.intent == IntentType.PRODUCTIVITY_TIMER
    assert result.confidence >= 0.8
    assert result.entities.get("duration") == 5
    assert result.entities.get("unit") == "minutes"


def test_calculation_classification():
    classifier = IntentClassifier()
    result = classifier.classify("Calculate 15 * 8")
    assert result.intent == IntentType.CALCULATION_MATH
    assert result.confidence >= 0.8
    assert "15 * 8" in result.entities.get("expression")


def test_percentage_calculation_classification():
    classifier = IntentClassifier()
    result = classifier.classify("Calculate 20% tip on $85")
    assert result.intent == IntentType.CALCULATION_MATH
    assert result.confidence >= 0.8


def test_note_creation_classification():
    classifier = IntentClassifier()
    result = classifier.classify("Take a note: Buy groceries and milk")
    assert result.intent == IntentType.FILE_NOTE_MANAGEMENT
    assert result.confidence >= 0.8
    assert "buy groceries" in result.entities.get("content", "").lower()


def test_system_status_classification():
    classifier = IntentClassifier()
    result = classifier.classify("Check system status and cpu usage")
    assert result.intent == IntentType.SYSTEM_CONTROL
    assert result.confidence >= 0.8


def test_greeting_classification():
    classifier = IntentClassifier()
    result = classifier.classify("Hello there, how are you?")
    assert result.intent == IntentType.CONVERSATIONAL_CHAT
    assert result.confidence >= 0.8
