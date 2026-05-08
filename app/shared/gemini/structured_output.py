"""
Structured output generation engine.

Core orchestrator that ties together Gemini, retry logic, and validation.
"""

from typing import Type, TypeVar, Generic

from pydantic import BaseModel, ValidationError

from app.shared.gemini.client import model
from app.shared.gemini.parser import parse_gemini_response, ParsingError
from app.shared.retry.retry_engine import retry_on_malformed_json, RetryConfig

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """Raised when structured output generation fails."""

    pass


class StructuredOutputGenerator(Generic[T]):
    """
    Generic structured output generator for any Pydantic schema.

    Pipeline:
    1. Generate response from Gemini
    2. Retry on failures
    3. Clean and parse JSON
    4. Validate against Pydantic schema
    5. Return validated object
    """

    def __init__(self, schema: Type[T]):
        """Initialize generator with target schema."""
        self.schema = schema
        self.max_retries = RetryConfig.MAX_ATTEMPTS

    def generate(self, prompt: str) -> T:
        """
        Generate and validate structured output from prompt.

        Args:
            prompt: Instruction prompt for Gemini

        Returns:
            Validated instance of target schema

        Raises:
            StructuredOutputError: If generation or validation fails
        """
        try:
            response = self._generate_with_retry(prompt)
            parsed_data = parse_gemini_response(response)
            validated = self.schema(**parsed_data)
            return validated

        except ParsingError as e:
            raise StructuredOutputError(f"Parsing failed: {str(e)}") from e
        except ValidationError as e:
            raise StructuredOutputError(f"Validation failed: {str(e)}") from e
        except Exception as e:
            raise StructuredOutputError(f"Unexpected error: {str(e)}") from e

    @retry_on_malformed_json(
        max_attempts=RetryConfig.MAX_ATTEMPTS,
        initial_wait=RetryConfig.INITIAL_WAIT,
        max_wait=RetryConfig.MAX_WAIT,
    )
    def _generate_with_retry(self, prompt: str) -> str:
        """Call Gemini with retry on malformed JSON."""
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise StructuredOutputError(f"Gemini API call failed: {str(e)}") from e


def generate_structured_output(
    prompt: str,
    schema: Type[T],
) -> T:
    """
    Generate and validate structured output from Gemini.

    Args:
        prompt: Instruction prompt for Gemini
        schema: Pydantic model to validate against

    Returns:
        Validated instance of schema

    Raises:
        StructuredOutputError: If generation or validation fails
    """
    generator = StructuredOutputGenerator(schema)
    return generator.generate(prompt)
