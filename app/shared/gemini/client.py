"""Centralized Gemini client/model bootstrap."""

from __future__ import annotations

import google.generativeai as genai

from app.config import settings


def _resolve_model_name() -> str:
    preferred = settings.GEMINI_MODEL.strip()
    if preferred in {"gemini-1.5-pro", "models/gemini-1.5-pro"}:
        preferred = "gemini-1.5-pro-latest"

    candidates = [preferred, "models/gemini-1.5-pro-latest", "gemini-1.5-pro-latest", "models/gemini-1.5-pro"]

    try:
        available = list(genai.list_models())
    except Exception:
        return preferred

    supported = {
        m.name
        for m in available
        if "generateContent" in getattr(m, "supported_generation_methods", [])
    }

    for candidate in candidates:
        candidate_with_prefix = candidate if candidate.startswith("models/") else f"models/{candidate}"
        if candidate in supported:
            return candidate
        if candidate_with_prefix in supported:
            return candidate_with_prefix

    for model_name in supported:
        if "gemini-1.5-pro" in model_name:
            return model_name

    return preferred


def _build_model() -> genai.GenerativeModel:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model_name = _resolve_model_name()
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config={
            "temperature": 0.2,
            "top_p": 0.9,
            "max_output_tokens": 1024,
        },
    )


model = _build_model()
