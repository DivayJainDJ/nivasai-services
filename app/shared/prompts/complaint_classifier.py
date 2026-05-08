"""
Complaint classifier prompt template.
"""

COMPLAINT_CLASSIFIER_PROMPT = """You are an expert urban complaint classifier for a civic intelligence platform.

Analyze the following complaint and classify it into exactly one category.

Complaint Text:
{complaint_text}

Return ONLY valid JSON with NO markdown wrappers or additional text:
{{
    "category": "<one of: water_sanitation, waste_management, road_infrastructure, electricity, street_lighting, park_maintenance, drainage, public_health, pollution, other>",
    "severity": "<one of: low, medium, high, critical>",
    "summary": "<concise 1-2 sentence summary>",
    "department": "<one of: water_board, sanitation, roads, electricity, parks, drainage, health, pollution, other>",
    "confidence": <0.0 to 1.0>
}}

Guidelines:
- Confidence: 0.0=uncertain, 1.0=very confident
- Severity: critical=immediate danger, high=significant impact, medium=needs attention, low=minor
- Always return valid JSON only
"""


def get_complaint_classifier_prompt(complaint_text: str) -> str:
    """Generate complaint classifier prompt."""
    if not complaint_text or len(complaint_text.strip()) < 10:
        raise ValueError("Complaint text must be at least 10 characters")
    return COMPLAINT_CLASSIFIER_PROMPT.format(complaint_text=complaint_text.strip())
