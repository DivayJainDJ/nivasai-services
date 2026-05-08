"""
Prompts for complaint classification using Gemini AI
"""

from typing import Dict, Any, List
from datetime import datetime


def get_classification_prompt(description: str) -> str:
    """
    Generate comprehensive prompt for complaint classification
    
    Args:
        description: User's complaint description
        
    Returns:
        Complete prompt for Gemini AI
    """
    
    prompt = f"""
You are an expert civic complaint classifier for NivasAI, a platform that processes complaints from Indian citizens about urban infrastructure and services.

Your task is to analyze the following complaint and classify it accurately.

COMPLAINT DESCRIPTION:
"{description}"

CLASSIFICATION REQUIREMENTS:

1. CATEGORY: Classify into one of these categories:
   - water: Water supply, tankers, connections, leaks, borewells
   - sanitation: Drains, sewers, toilets, garbage, waste management
   - roads: Potholes, street repairs, footpaths, bridges, traffic
   - electricity: Power supply, street lights, transformers, connections
   - housing: Building repairs, leaks, construction, maintenance
   - waste: Garbage collection, dumping grounds, recycling
   - street_lights: Street lighting, pole repairs, bulb replacement
   - drainage: Waterlogging, drain blockage, flooding
   - eviction: Demolition threats, illegal encroachments
   - noise: Noise pollution, loudspeakers, construction noise
   - other: Anything not covered above

2. SEVERITY: Assess urgency:
   - critical: Life-threatening, emergency, immediate danger
   - high: Major disruption, health hazard, significant damage
   - medium: Moderate issue, affects daily life
   - low: Minor inconvenience, improvement request

3. CONFIDENCE: How confident are you in this classification? (0.0 to 1.0)

4. SUMMARY: Brief one-sentence description of the issue

5. SUGGESTED DEPARTMENT: Which government department should handle this?
   - water: Water Board/Jal Board
   - sanitation: Municipal Corporation/Sanitation
   - roads: PWD/Road Department
   - electricity: Electricity Board/Power Corporation
   - housing: Housing Board/Urban Development
   - municipal: Municipal Corporation
   - health: Health Department
   - police: Police Department
   - fire: Fire Department

6. KEYWORDS: Extract 5-10 relevant keywords from the complaint

CONTEXT FOR INDIAN URBAN SETTINGS:
- Consider local languages (Hindi, regional languages) mixed with English
- Common terms: naali (drain), kachra (garbage), sadak (road), bijli (electricity)
- Slum areas and informal settlements have different priorities
- Monsoon season affects drainage and waterlogging issues
- Government schemes like PMAY, Smart Cities may be relevant

RESPONSE FORMAT:
Provide your response as a valid JSON object exactly like this:

{{
    "category": "category_name",
    "severity": "severity_level",
    "confidence": 0.85,
    "summary": "Brief description of the issue",
    "suggested_department": "department_name",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

IMPORTANT:
- Respond with ONLY the JSON object, no additional text
- Ensure all JSON fields are included
- Confidence should be realistic (0.5-0.95 for typical cases)
- Consider both English and Hindi/Indian language terms
- Think about the human impact when assessing severity

Now classify the complaint:
"""
    
    return prompt


def get_image_analysis_prompt(description: str) -> str:
    """
    Generate prompt for analyzing complaint with image
    
    Args:
        description: User's complaint description
        
    Returns:
        Prompt for image analysis
    """
    
    prompt = f"""
You are analyzing a civic complaint that includes both text description and an image.

TEXT DESCRIPTION:
"{description}"

IMAGE ANALYSIS TASKS:

1. VISUAL ELEMENTS: Identify what you can see in the image:
   - Infrastructure elements (roads, drains, buildings, etc.)
   - Problem indicators (leaks, damage, blockages, etc.)
   - Location context (slum area, residential, commercial)
   - Severity indicators (size of problem, affected area)

2. IMAGE VALIDATION: Check if the image is:
   - Relevant to the complaint description
   - Clear enough to identify the issue
   - Shows the actual problem location

3. ENHANCED CLASSIFICATION: Use both text and image to determine:
   - More accurate category based on visual evidence
   - Adjusted severity based on visual impact
   - Confidence level (higher if image confirms text)

4. VISUAL KEYWORDS: Extract visual elements as keywords

RESPONSE FORMAT:
{{
    "visual_elements": ["element1", "element2", "element3"],
    "image_relevance": "high/medium/low",
    "visual_severity": "critical/high/medium/low",
    "enhanced_category": "category_name",
    "enhanced_severity": "severity_level",
    "confidence_boost": 0.1,
    "visual_keywords": ["visual1", "visual2", "visual3"],
    "analysis_summary": "Brief summary of what the image shows"
}}

Analyze the image and provide the JSON response:
"""
    
    return prompt


def get_batch_classification_prompt(complaints: List[Dict[str, Any]]) -> str:
    """
    Generate prompt for batch classification of multiple complaints
    
    Args:
        complaints: List of complaint data
        
    Returns:
        Prompt for batch processing
    """
    
    complaints_text = ""
    for i, complaint in enumerate(complaints, 1):
        complaints_text += f"""
COMPLAINT {i}:
ID: {complaint.get('id', f'complaint_{i}')}
Description: "{complaint.get('description', '')}"
"""
        if complaint.get('has_image'):
            complaints_text += "Has Image: Yes\n"
        complaints_text += "---\n"
    
    prompt = f"""
You are processing multiple civic complaints for batch classification.

{complaints_text}

BATCH CLASSIFICATION TASK:

For each complaint, provide classification in this format:

{{
    "complaint_{id}": {{
        "category": "category_name",
        "severity": "severity_level", 
        "confidence": 0.85,
        "summary": "Brief description",
        "suggested_department": "department_name",
        "keywords": ["keyword1", "keyword2", "keyword3"]
    }}
}}

RESPONSE FORMAT:
Provide a single JSON object with all classifications:

{{
    "classifications": {{
        "complaint_1": {{...}},
        "complaint_2": {{...}},
        ...
    }},
    "batch_summary": {{
        "total_processed": {len(complaints)},
        "categories_found": ["category1", "category2"],
        "severity_distribution": {{"critical": 1, "high": 2, "medium": 3, "low": 4}},
        "avg_confidence": 0.82
    }}
}}

Process all complaints and return the JSON response:
"""
    
    return prompt


def get_reclassification_prompt(
    original_classification: Dict[str, Any],
    new_description: str,
    reason_for_reclassification: str
) -> str:
    """
    Generate prompt for reclassifying a complaint
    
    Args:
        original_classification: Previous classification result
        new_description: Updated complaint description
        reason_for_reclassification: Why reclassification is needed
        
    Returns:
        Prompt for reclassification
    """
    
    prompt = f"""
You are reclassifying a civic complaint based on new information.

ORIGINAL CLASSIFICATION:
{json.dumps(original_classification, indent=2)}

NEW DESCRIPTION:
"{new_description}"

RECLASSIFICATION REASON:
{reason_for_reclassification}

RECLASSIFICATION TASK:

1. Compare new description with original classification
2. Update category, severity, and confidence if needed
3. Explain what changed and why
4. Maintain consistency with previous classification if still valid

RESPONSE FORMAT:
{{
    "updated_classification": {{
        "category": "category_name",
        "severity": "severity_level",
        "confidence": 0.85,
        "summary": "Updated description",
        "suggested_department": "department_name",
        "keywords": ["keyword1", "keyword2", "keyword3"]
    }},
    "changes_made": {{
        "category_changed": true/false,
        "severity_changed": true/false,
        "confidence_changed": true/false,
        "reason_for_changes": "Explanation of what changed and why"
    }},
    "reclassification_confidence": 0.90,
    "recommendation": "keep_original/update/new_classification"
}}

Provide the JSON response:
"""
    
    return prompt


def get_quality_check_prompt(classification: Dict[str, Any], description: str) -> str:
    """
    Generate prompt for quality checking classification results
    
    Args:
        classification: Classification result to check
        description: Original complaint description
        
    Returns:
        Prompt for quality check
    """
    
    prompt = f"""
You are quality-checking a complaint classification result.

COMPLAINT DESCRIPTION:
"{description}"

CLASSIFICATION RESULT:
{json.dumps(classification, indent=2)}

QUALITY CHECK TASK:

1. ACCURACY: Does the category match the description?
2. SEVERITY: Is the severity level appropriate?
3. CONFIDENCE: Is the confidence score realistic?
4. COMPLETENESS: Are all required fields present?
5. CONSISTENCY: Do the summary and keywords align with category?

QUALITY CRITERIA:
- Category must directly relate to the main issue described
- Severity should reflect actual impact on citizens
- Confidence should be lower for ambiguous descriptions
- Summary should be concise and accurate
- Keywords should be relevant and specific

RESPONSE FORMAT:
{{
    "quality_score": 0.85,
    "issues_found": [
        {{
            "field": "category",
            "issue": "Category mismatch",
            "suggestion": "Change to sanitation"
        }}
    ],
    "accuracy_rating": "high/medium/low",
    "confidence_rating": "high/medium/low", 
    "completeness_rating": "high/medium/low",
    "overall_assessment": "excellent/good/fair/poor",
    "recommendations": [
        "Recommendation 1",
        "Recommendation 2"
    ]
}}

Provide the quality check JSON response:
"""
    
    return prompt


def get_multilingual_support_prompt(description: str, detected_languages: List[str]) -> str:
    """
    Generate prompt for handling multilingual complaints
    
    Args:
        description: Complaint description (may contain multiple languages)
        detected_languages: List of detected languages
        
    Returns:
        Prompt for multilingual classification
    """
    
    prompt = f"""
You are classifying a multilingual civic complaint from India.

COMPLAINT DESCRIPTION:
"{description}"

DETECTED LANGUAGES: {', '.join(detected_languages)}

MULTILINGUAL CLASSIFICATION TASK:

1. LANGUAGE ANALYSIS:
   - Identify primary language(s)
   - Translate key terms if needed
   - Understand code-switching patterns

2. CULTURAL CONTEXT:
   - Consider local terminology
   - Understand regional complaint patterns
   - Account for urban vs rural contexts

3. CLASSIFICATION ACCURACY:
   - Focus on intent, not language
   - Use visual cues if available
   - Consider common local issues

SPECIAL CONSIDERATIONS:
- Hindi-English code switching (Hinglish) is common
- Regional terms may vary by city/state
- Slum areas have different infrastructure priorities
- Government scheme names may be mentioned

RESPONSE FORMAT:
{{
    "primary_language": "hindi/english/regional",
    "language_confidence": 0.9,
    "translated_keywords": ["keyword1", "keyword2"],
    "cultural_context": "urban_slum/formal_housing/rural",
    "classification": {{
        "category": "category_name",
        "severity": "severity_level",
        "confidence": 0.85,
        "summary": "Brief description",
        "suggested_department": "department_name",
        "keywords": ["keyword1", "keyword2", "keyword3"]
    }},
    "multilingual_notes": "Any special notes about language handling"
}}

Provide the multilingual classification JSON response:
"""
    
    return prompt


# Helper function to get the appropriate prompt based on context
def get_classification_prompt_by_context(
    description: str,
    has_image: bool = False,
    is_batch: bool = False,
    is_reclassification: bool = False,
    is_quality_check: bool = False,
    is_multilingual: bool = False,
    context: Dict[str, Any] = None
) -> str:
    """
    Get the appropriate classification prompt based on context
    
    Args:
        description: Complaint description
        has_image: Whether image is available
        is_batch: Whether this is batch processing
        is_reclassification: Whether this is reclassification
        is_quality_check: Whether this is quality check
        is_multilingual: Whether multilingual support is needed
        context: Additional context data
        
    Returns:
        Appropriate prompt for the context
    """
    
    if is_quality_check and context:
        return get_quality_check_prompt(context.get('classification', {}), description)
    
    elif is_reclassification and context:
        return get_reclassification_prompt(
            context.get('original_classification', {}),
            description,
            context.get('reason', 'User requested reclassification')
        )
    
    elif is_batch and context:
        return get_batch_classification_prompt(context.get('complaints', []))
    
    elif is_multilingual and context:
        return get_multilingual_support_prompt(description, context.get('detected_languages', ['english']))
    
    elif has_image:
        return get_image_analysis_prompt(description)
    
    else:
        return get_classification_prompt(description)
