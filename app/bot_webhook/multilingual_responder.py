"""Multilingual response generation."""

from __future__ import annotations

from typing import Any


class MultilingualResponder:
    """Generate multilingual responses."""

    def __init__(self):
        """Initialize responder."""
        self.responses = {
            "greet": {
                "en": "Hello! 👋 Welcome to NivasAI. I can help you with:\n\n"
                      "📝 File complaints\n"
                      "🔍 Check complaint status\n"
                      "🏠 Find housing\n"
                      "📄 Upload documents\n"
                      "ℹ️ Get ward information\n\n"
                      "How can I assist you today?",
                "hi": "नमस्ते! 👋 NivasAI में आपका स्वागत है। मैं आपकी मदद कर सकता हूं:\n\n"
                      "📝 शिकायत दर्ज करें\n"
                      "🔍 शिकायत की स्थिति जांचें\n"
                      "🏠 आवास खोजें\n"
                      "📄 दस्तावेज़ अपलोड करें\n"
                      "ℹ️ वार्ड जानकारी प्राप्त करें\n\n"
                      "मैं आज आपकी कैसे सहायता कर सकता हूं?",
            },
            "complaint_need_image": {
                "en": "To file a complaint, please send a photo of the issue along with a description.",
                "hi": "शिकायत दर्ज करने के लिए, कृपया समस्या की एक तस्वीर और विवरण भेजें।",
            },
            "complaint_still_need_image": {
                "en": "I still need a photo to file your complaint. Please send an image.",
                "hi": "मुझे अभी भी आपकी शिकायत दर्ज करने के लिए एक तस्वीर चाहिए। कृपया एक छवि भेजें।",
            },
            "complaint_filed": {
                "en": "✅ Your complaint has been filed successfully!\n\n"
                      "Complaint ID: {complaint_id}\n\n"
                      "You can check the status anytime by sending the complaint ID.",
                "hi": "✅ आपकी शिकायत सफलतापूर्वक दर्ज कर दी गई है!\n\n"
                      "शिकायत ID: {complaint_id}\n\n"
                      "आप शिकायत ID भेजकर किसी भी समय स्थिति जांच सकते हैं।",
            },
            "status_need_id": {
                "en": "Please provide your complaint ID to check the status.",
                "hi": "स्थिति जांचने के लिए कृपया अपनी शिकायत ID प्रदान करें।",
            },
            "status_not_found": {
                "en": "Sorry, I couldn't find complaint {complaint_id}. Please check the ID and try again.",
                "hi": "क्षमा करें, मुझे शिकायत {complaint_id} नहीं मिली। कृपया ID जांचें और पुनः प्रयास करें।",
            },
            "status_found": {
                "en": "📋 Complaint Status\n\n"
                      "ID: {complaint_id}\n"
                      "Status: {status}\n"
                      "Category: {category}\n\n"
                      "We're working on resolving your issue.",
                "hi": "📋 शिकायत की स्थिति\n\n"
                      "ID: {complaint_id}\n"
                      "स्थिति: {status}\n"
                      "श्रेणी: {category}\n\n"
                      "हम आपकी समस्या को हल करने पर काम कर रहे हैं।",
            },
            "housing_start": {
                "en": "🏠 Let's find housing for you!\n\n"
                      "What is your annual household income (in ₹)?",
                "hi": "🏠 आइए आपके लिए आवास खोजें!\n\n"
                      "आपकी वार्षिक घरेलू आय (₹ में) क्या है?",
            },
            "housing_ask_family": {
                "en": "How many family members do you have?",
                "hi": "आपके परिवार में कितने सदस्य हैं?",
            },
            "housing_invalid_income": {
                "en": "Please provide a valid income amount in numbers.",
                "hi": "कृपया संख्या में एक वैध आय राशि प्रदान करें।",
            },
            "housing_invalid_family": {
                "en": "Please provide a valid family size (1-20 members).",
                "hi": "कृपया एक वैध परिवार का आकार प्रदान करें (1-20 सदस्य)।",
            },
            "housing_result": {
                "en": "Based on your income of ₹{income}, you are eligible for {eligibility} category housing.\n\n"
                      "We'll help you find suitable options!",
                "hi": "₹{income} की आपकी आय के आधार पर, आप {eligibility} श्रेणी के आवास के लिए पात्र हैं।\n\n"
                      "हम आपको उपयुक्त विकल्प खोजने में मदद करेंगे!",
            },
            "document_upload": {
                "en": "📄 Please send your document image.\n\n"
                      "Supported: Aadhaar, Income Certificate, Ration Card",
                "hi": "📄 कृपया अपना दस्तावेज़ चित्र भेजें।\n\n"
                      "समर्थित: आधार, आय प्रमाण पत्र, राशन कार्ड",
            },
            "ward_info": {
                "en": "ℹ️ Ward information is being prepared. Please check back soon!",
                "hi": "ℹ️ वार्ड की जानकारी तैयार की जा रही है। कृपया जल्द ही वापस जांचें!",
            },
            "unknown": {
                "en": "I'm not sure I understand. You can:\n\n"
                      "• File a complaint\n"
                      "• Check complaint status\n"
                      "• Find housing\n"
                      "• Upload documents\n\n"
                      "What would you like to do?",
                "hi": "मुझे यकीन नहीं है कि मैं समझता हूं। आप कर सकते हैं:\n\n"
                      "• शिकायत दर्ज करें\n"
                      "• शिकायत की स्थिति जांचें\n"
                      "• आवास खोजें\n"
                      "• दस्तावेज़ अपलोड करें\n\n"
                      "आप क्या करना चाहेंगे?",
            },
            "error": {
                "en": "Sorry, something went wrong. Please try again.",
                "hi": "क्षमा करें, कुछ गलत हो गया। कृपया पुन: प्रयास करें।",
            },
        }

    def get_response(
        self,
        key: str,
        language: str = "en",
        **kwargs: Any,
    ) -> str:
        """
        Get response in specified language.
        
        Args:
            key: Response key
            language: Language code (en/hi)
            **kwargs: Format parameters
        
        Returns:
            Formatted response string
        """
        if key not in self.responses:
            return self.responses["unknown"][language]
        
        template = self.responses[key].get(language, self.responses[key]["en"])
        
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
