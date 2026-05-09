"""Handle housing search workflow."""

from __future__ import annotations

from app.bot_webhook.multilingual_responder import MultilingualResponder
from app.bot_webhook.schemas import BotSession, HandlerResponse
from app.bot_webhook.session_manager import SessionManager
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class HousingHandler:
    """Handle housing search workflow."""

    def __init__(self):
        """Initialize housing handler."""
        self.session_manager = SessionManager()
        self.responder = MultilingualResponder()

    def handle(
        self,
        session: BotSession,
        message: str,
    ) -> HandlerResponse:
        """
        Handle housing search.
        
        Args:
            session: Current session
            message: User message
        
        Returns:
            HandlerResponse
        """
        try:
            language = session.preferredLanguage
            workflow_state = session.workflowState
            
            if not workflow_state:
                # Start housing workflow
                response_msg = self.responder.get_response(
                    "housing_start",
                    language,
                )
                
                self.session_manager.update_session(
                    session.phone,
                    intent="FIND_HOUSING",
                    workflow_state="collecting_income",
                )
                
                return HandlerResponse(
                    message=response_msg,
                    nextState="collecting_income",
                )
            
            elif workflow_state == "collecting_income":
                # Extract income
                income = self._extract_number(message)
                
                if income:
                    # Store income
                    self.session_manager.update_session(
                        session.phone,
                        workflow_state="collecting_family_size",
                        context_update={"income": income},
                    )
                    
                    response_msg = self.responder.get_response(
                        "housing_ask_family",
                        language,
                    )
                    
                    return HandlerResponse(
                        message=response_msg,
                        nextState="collecting_family_size",
                    )
                else:
                    response_msg = self.responder.get_response(
                        "housing_invalid_income",
                        language,
                    )
                    return HandlerResponse(message=response_msg)
            
            elif workflow_state == "collecting_family_size":
                # Extract family size
                family_size = self._extract_number(message)
                
                if family_size and 1 <= family_size <= 20:
                    # Store family size
                    income = self.session_manager.get_context(session.phone, "income")
                    
                    # Determine eligibility
                    eligibility = self._determine_eligibility(income, family_size)
                    
                    response_msg = self.responder.get_response(
                        "housing_result",
                        language,
                        eligibility=eligibility,
                        income=income,
                    )
                    
                    # Clear workflow
                    self.session_manager.clear_workflow(session.phone)
                    
                    return HandlerResponse(message=response_msg)
                else:
                    response_msg = self.responder.get_response(
                        "housing_invalid_family",
                        language,
                    )
                    return HandlerResponse(message=response_msg)
            
            else:
                # Unknown state
                self.session_manager.clear_workflow(session.phone)
                response_msg = self.responder.get_response(
                    "housing_start",
                    language,
                )
                return HandlerResponse(message=response_msg)
        
        except Exception as exc:
            logger.error("housing_handler_failed", error=str(exc))
            return HandlerResponse(
                message=self.responder.get_response("error", session.preferredLanguage),
                success=False,
            )

    def _extract_number(self, message: str) -> int | None:
        """Extract number from message."""
        import re
        
        # Remove commas and extract digits
        numbers = re.findall(r"\d+", message.replace(",", ""))
        
        if numbers:
            try:
                return int(numbers[0])
            except:
                return None
        
        return None

    def _determine_eligibility(self, income: int, family_size: int) -> str:
        """Determine housing eligibility."""
        if income <= 300000:
            return "EWS"
        elif income <= 600000:
            return "LIG"
        elif income <= 1800000:
            return "MIG"
        else:
            return "Not Eligible"
