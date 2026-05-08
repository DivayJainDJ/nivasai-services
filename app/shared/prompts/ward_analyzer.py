"""
Ward analyzer prompt template.
"""

WARD_ANALYZER_PROMPT = """Analyze this satellite imagery of a ward and assess infrastructure quality.

Ward Details:
- Ward ID: {ward_id}
- Location: {location}
- Image: {image_data}

Analyze and return JSON with infrastructure scores (0-100 scale):
{{
    "infrastructure_scores": {{
        "roads": <0-100>,
        "drainage": <0-100>,
        "street_lighting": <0-100>,
        "water_supply": <0-100>,
        "sanitation": <0-100>,
        "overall": <0-100>
    }},
    "pressure_level": "<low|medium|high|critical>",
    "recommendations": ["recommendation 1", "recommendation 2", ...]
}}

Return ONLY valid JSON.
"""


def get_ward_analyzer_prompt(ward_id: str, location: str, image_data: str) -> str:
    """Generate ward analyzer prompt."""
    return WARD_ANALYZER_PROMPT.format(
        ward_id=ward_id, location=location, image_data=image_data
    )
