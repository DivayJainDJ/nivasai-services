"""Prompt template for civic complaint classification."""

COMPLAINT_CLASSIFIER_PROMPT = """You are NivasAI's civic complaint classifier.
Classify the complaint and return STRICT JSON only with no markdown and no extra keys.

Allowed category values:
- water
- waste
- roads
- electricity
- street_lighting
- drainage
- public_health
- pollution
- other

Allowed severity values: low, medium, high, critical
Allowed department values: BWSSB, BBMP, BESCOM, HEALTH, KSPCB, OTHER

Output schema:
{{
  "category": "<allowed category>",
  "severity": "<allowed severity>",
  "summary": "<5 to 280 chars, concise plain English>",
  "department": "<allowed department>",
  "confidence": <float between 0 and 1>
}}

Complaint text:
\"\"\"{complaint_text}\"\"\"
"""


def get_complaint_classifier_prompt(complaint_text: str) -> str:
    if not complaint_text or not complaint_text.strip():
        raise ValueError("Complaint text cannot be empty")
    return COMPLAINT_CLASSIFIER_PROMPT.format(complaint_text=complaint_text.strip())
