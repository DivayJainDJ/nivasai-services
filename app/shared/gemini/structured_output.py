"""Generic typed structured output pipeline for Gemini."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import RetryError

from app.shared.gemini.client import model
from app.shared.gemini.parser import GeminiParsingError, extract_response_text, parse_gemini_response_to_dict
from app.shared.retry.retry_engine import (
    RetryableGeminiError,
    RetryableParseError,
    with_exponential_retry,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredOutputError(Exception):
    """Final pipeline error surfaced to caller."""


@with_exponential_retry()
def _run_structured_generation_once(prompt: str, schema: type[SchemaT]) -> SchemaT:
    try:
        response = model.generate_content(prompt)
        raw_text = extract_response_text(response)
    except TimeoutError:
        raise
    except Exception as exc:
        raise RetryableGeminiError(f"Gemini invocation failed: {exc}") from exc

    try:
        payload = parse_gemini_response_to_dict(raw_text)
        return schema.model_validate(payload)
    except (GeminiParsingError, ValidationError) as exc:
        raise RetryableParseError(str(exc)) from exc


def generate_structured_output(prompt: str, schema: type[SchemaT]) -> SchemaT:
    """Generate strict schema-validated output from a prompt."""
    if not prompt or not prompt.strip():
        raise StructuredOutputError("Prompt cannot be empty")

    try:
        return _run_structured_generation_once(prompt=prompt.strip(), schema=schema)
    except RetryError as exc:
        raise StructuredOutputError(f"Structured output failed after retries: {exc}") from exc
    except (RetryableGeminiError, RetryableParseError, TimeoutError) as exc:
        raise StructuredOutputError(f"Structured output failed: {exc}") from exc
