"""Tests for intent classifier."""

from __future__ import annotations

import pytest

from app.whatsapp_agent.intent_classifier import create_fallback_intent


def test_fallback_intent_greeting():
    """Test fallback intent for greetings."""
    intent = create_fallback_intent("Hello")
    assert intent.intent == "greeting"
    assert intent.confidence > 0


def test_fallback_intent_status():
    """Test fallback intent for status tracking."""
    intent = create_fallback_intent("Track complaint 123")
    assert intent.intent == "complaint_status"
    assert intent.confidence > 0


def test_fallback_intent_housing():
    """Test fallback intent for housing."""
    intent = create_fallback_intent("I need housing")
    assert intent.intent == "housing_help"
    assert intent.confidence > 0


def test_fallback_intent_hindi():
    """Test fallback intent with Hindi text."""
    intent = create_fallback_intent("मुझे घर चाहिए")
    assert intent.intent == "housing_help"
    assert intent.language == "hi"


def test_fallback_intent_unknown():
    """Test fallback intent for unknown message."""
    intent = create_fallback_intent("random text xyz")
    assert intent.intent == "unknown"
