"""Tests for validator utilities."""

from __future__ import annotations

import pytest

from app.whatsapp_agent.validator import (
    clean_text,
    extract_complaint_id,
    extract_phone_number,
    is_greeting,
)


def test_extract_phone_number():
    """Test phone number extraction."""
    phone = extract_phone_number("whatsapp:+1234567890")
    assert phone == "+1234567890"


def test_extract_complaint_id():
    """Test complaint ID extraction."""
    # Test with long alphanumeric ID (Firestore style)
    complaint_id = extract_complaint_id("Track complaint abc123def456ghi789jk")
    assert complaint_id == "abc123def456ghi789jk"
    
    # Test with hash prefix
    complaint_id = extract_complaint_id("#abc123def456ghi789jk")
    assert complaint_id == "abc123def456ghi789jk"


def test_is_greeting():
    """Test greeting detection."""
    assert is_greeting("Hello") is True
    assert is_greeting("Hi there") is True
    assert is_greeting("Namaste") is True
    assert is_greeting("नमस्ते") is True
    assert is_greeting("Track complaint") is False


def test_clean_text():
    """Test text cleaning."""
    cleaned = clean_text("  Hello   world!  ")
    assert cleaned == "Hello world!"
    
    cleaned = clean_text("Test@#$%text")
    assert cleaned == "Testtext"
