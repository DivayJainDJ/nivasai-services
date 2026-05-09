"""Handle housing assistance requests."""

from __future__ import annotations

from app.housing_matcher.service import match_housing
from app.shared.logging.logger import get_logger
from app.whatsapp_agent.conversation_manager import ConversationManager
from app.whatsapp_agent.schemas import HousingRecommendation

logger = get_logger(__name__)


class HousingHandlerError(Exception):
    """Raised when housing handling fails."""


def start_housing_workflow(phone_number: str) -> str:
    """Start housing assistance workflow."""
    conv_manager = ConversationManager(phone_number)
    conv_manager.start_workflow("housing_assistance", {"step": "collect_income"})
    
    return (
        "🏠 Housing Assistance\n\n"
        "I'll help you find affordable housing options.\n\n"
        "Please provide the following information:\n"
        "1. Your monthly income (in ₹)\n\n"
        "Example: 25000"
    )


def collect_housing_data(phone_number: str, message: str) -> str:
    """Collect housing data step by step."""
    conv_manager = ConversationManager(phone_number)
    workflow_data = conv_manager.get_workflow_data()
    current_step = workflow_data.get("step", "collect_income")
    
    if current_step == "collect_income":
        # Parse income
        try:
            income = int(message.replace(",", "").replace("₹", "").strip())
            if income <= 0:
                return "Please enter a valid monthly income (greater than 0)."
            
            workflow_data["monthlyIncome"] = income
            workflow_data["step"] = "collect_family_size"
            conv_manager.update_workflow_data(workflow_data)
            
            return (
                f"✅ Monthly income: ₹{income:,}\n\n"
                "2. How many people are in your family?\n\n"
                "Example: 4"
            )
        except ValueError:
            return "Please enter a valid number for monthly income.\n\nExample: 25000"
    
    elif current_step == "collect_family_size":
        # Parse family size
        try:
            family_size = int(message.strip())
            if family_size <= 0 or family_size > 20:
                return "Please enter a valid family size (1-20)."
            
            workflow_data["familySize"] = family_size
            workflow_data["step"] = "collect_city"
            conv_manager.update_workflow_data(workflow_data)
            
            return (
                f"✅ Family size: {family_size}\n\n"
                "3. Which city are you looking for housing in?\n\n"
                "Example: Bangalore"
            )
        except ValueError:
            return "Please enter a valid number for family size.\n\nExample: 4"
    
    elif current_step == "collect_city":
        # Parse city
        city = message.strip()
        if len(city) < 2:
            return "Please enter a valid city name."
        
        workflow_data["city"] = city
        workflow_data["step"] = "collect_category"
        conv_manager.update_workflow_data(workflow_data)
        
        return (
            f"✅ City: {city}\n\n"
            "4. What is your category?\n\n"
            "Options: general, sc, st, obc\n\n"
            "Example: general"
        )
    
    elif current_step == "collect_category":
        # Parse category
        category = message.strip().lower()
        valid_categories = ["general", "sc", "st", "obc"]
        
        if category not in valid_categories:
            return f"Please enter a valid category: {', '.join(valid_categories)}"
        
        workflow_data["category"] = category
        workflow_data["step"] = "ready"
        conv_manager.update_workflow_data(workflow_data)
        
        return (
            f"✅ Category: {category}\n\n"
            "Great! I have all the information.\n"
            "Searching for housing options...\n\n"
            "⏳ Please wait..."
        )
    
    return "Something went wrong. Please start over by typing 'housing help'."


def generate_housing_recommendations(phone_number: str) -> str:
    """Generate housing recommendations."""
    conv_manager = ConversationManager(phone_number)
    workflow_data = conv_manager.get_workflow_data()
    
    # Check if we have all required data
    required_fields = ["monthlyIncome", "familySize", "city", "category"]
    if not all(field in workflow_data for field in required_fields):
        return "Missing information. Please start over by typing 'housing help'."
    
    try:
        # Call housing matcher
        citizen_data = {
            "citizenName": phone_number,
            "monthlyIncome": workflow_data["monthlyIncome"],
            "familySize": workflow_data["familySize"],
            "city": workflow_data["city"],
            "latitude": 0.0,  # Default location
            "longitude": 0.0,
            "category": workflow_data["category"],
            "preferredLanguage": conv_manager.get_preferred_language(),
            "urgencyLevel": "medium",
        }
        
        response = match_housing(citizen_data)
        
        # Complete workflow
        conv_manager.complete_workflow()
        
        # Format response
        if not response.matches:
            return (
                "❌ No housing units found matching your criteria.\n\n"
                f"Income: ₹{workflow_data['monthlyIncome']:,}\n"
                f"Family size: {workflow_data['familySize']}\n"
                f"City: {workflow_data['city']}\n"
                f"Category: {workflow_data['category']}\n\n"
                "Please try:\n"
                "- Different city\n"
                "- Adjusting your requirements\n"
                "- Contacting your local housing office"
            )
        
        # Build message with top matches
        message_parts = [
            "🏠 Housing Recommendations\n",
            f"Found {len(response.matches)} suitable options:\n",
        ]
        
        for i, match in enumerate(response.matches, 1):
            message_parts.extend([
                f"\n{i}. {match.scheme} - {match.city}",
                f"   Price: ₹{match.priceINR:,}",
                f"   Distance: {match.distanceKm} km",
                f"   Match Score: {match.score:.1f}/100",
                f"   {match.address}",
            ])
        
        message_parts.extend([
            "\n📄 Documents needed:",
            "- Aadhaar card",
            "- Income certificate",
            "- Ration card",
            "- Domicile certificate",
            "\n📞 Next steps:",
            "Visit your nearest housing office with these documents to apply.",
        ])
        
        return "\n".join(message_parts)
    
    except Exception as exc:
        logger.error("housing_recommendation_failed", phone=phone_number, error=str(exc))
        conv_manager.complete_workflow()
        return (
            "❌ Sorry, we couldn't generate housing recommendations at this time.\n\n"
            "Please try again later or contact your local housing office."
        )


def handle_housing_request(phone_number: str, message: str) -> str:
    """Handle housing assistance request."""
    conv_manager = ConversationManager(phone_number)
    
    # Check if workflow is active
    if not conv_manager.has_active_workflow():
        return start_housing_workflow(phone_number)
    
    workflow = conv_manager.get_active_workflow()
    
    if workflow == "housing_assistance":
        workflow_data = conv_manager.get_workflow_data()
        step = workflow_data.get("step", "collect_income")
        
        if step == "ready":
            # Generate recommendations
            return generate_housing_recommendations(phone_number)
        else:
            # Collect data
            return collect_housing_data(phone_number, message)
    
    return "Something went wrong. Please start over by typing 'housing help'."
