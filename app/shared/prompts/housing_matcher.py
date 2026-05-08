"""
Housing matcher prompt template.
"""

HOUSING_MATCHER_PROMPT = """Match a family with appropriate PMAY housing units based on eligibility and preferences.

Family Details:
- Family ID: {family_id}
- Family Size: {family_size}
- Income: {income}
- Ward Preference: {ward_preference}
- Location: {location}

Available Units:
{available_units}

Return JSON with ranked matches:
{{
    "matched_units": [
        {{
            "unit_id": "...",
            "match_score": <0-100>,
            "proximity_score": <0-100>
        }}
    ],
    "total_matches": <count>,
    "explanation": "Why these units match..."
}}

Return ONLY valid JSON.
"""


def get_housing_matcher_prompt(
    family_id: str, family_size: int, income: float, ward_preference: str, 
    location: str, available_units: str
) -> str:
    """Generate housing matcher prompt."""
    return HOUSING_MATCHER_PROMPT.format(
        family_id=family_id,
        family_size=family_size,
        income=income,
        ward_preference=ward_preference,
        location=location,
        available_units=available_units,
    )
