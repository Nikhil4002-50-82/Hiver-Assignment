
from typing import Optional
from src.schemas import AirlineIntent, TriageDecision


class TrivialBaselineAgent:

    def __init__(self):
        self.name = "Trivial Baseline (Keyword + Canned Reply)"

    def process_tweet(self, tweet_text: str, tweet_id: Optional[str] = None) -> TriageDecision:
        text_lower = tweet_text.lower()

        if "bag" in text_lower or "luggage" in text_lower or "suitcase" in text_lower:
            intent = AirlineIntent.BAGGAGE_SERVICES
            escalate = True
        elif "cancel" in text_lower or "delay" in text_lower or "flight" in text_lower:
            intent = AirlineIntent.FLIGHT_DISRUPTION
            escalate = True
        elif "refund" in text_lower or "compensation" in text_lower or "claim" in text_lower:
            intent = AirlineIntent.REFUNDS_COMPENSATION
            escalate = True
        elif "seat" in text_lower or "booking" in text_lower:
            intent = AirlineIntent.BOOKING_TICKETING
            escalate = True
        elif "check in" in text_lower or "boarding" in text_lower:
            intent = AirlineIntent.CHECKIN_BOARDING
            escalate = True
        elif "avios" in text_lower or "club" in text_lower:
            intent = AirlineIntent.LOYALTY_AVIOS
            escalate = True
        else:
            intent = AirlineIntent.GENERAL_INQUIRY
            escalate = False

        canned_reply = (
            "Thank you for reaching out to British Airways customer support. "
            "We have received your message and an agent will assist you shortly."
        )

        return TriageDecision(
            intent=intent,
            confidence_score=0.50,
            should_escalate_to_human=escalate,
            escalation_reason="Rule-based keyword trigger" if escalate else None,
            draft_reply=canned_reply,
            grounded_sources=[]
        )


class SimpleBaselineAgent:

    def __init__(self, api_key: str = "", model_name: str = "gemini-2.0-flash"):
        self.name = "Simple Baseline (Zero-Shot, No RAG)"
        self.api_key = api_key
        self.model_name = model_name

    def process_tweet(self, tweet_text: str, tweet_id: Optional[str] = None) -> TriageDecision:
        text_lower = tweet_text.lower()

        if "bag" in text_lower or "luggage" in text_lower:
            intent = AirlineIntent.BAGGAGE_SERVICES
            escalate = True
            reason = "Baggage assistance requested"
        elif "cancel" in text_lower or "delay" in text_lower:
            intent = AirlineIntent.FLIGHT_DISRUPTION
            escalate = True
            reason = "Flight schedule issue"
        elif "refund" in text_lower or "compensation" in text_lower or "claim" in text_lower:
            intent = AirlineIntent.REFUNDS_COMPENSATION
            escalate = True
            reason = "Financial claim"
        elif "seat" in text_lower or "book" in text_lower or "ticket" in text_lower:
            intent = AirlineIntent.BOOKING_TICKETING
            escalate = True
            reason = "Reservation modification"
        elif "check in" in text_lower:
            intent = AirlineIntent.CHECKIN_BOARDING
            escalate = False
            reason = None
        elif "avios" in text_lower:
            intent = AirlineIntent.LOYALTY_AVIOS
            escalate = False
            reason = None
        else:
            intent = AirlineIntent.GENERAL_INQUIRY
            escalate = False
            reason = None

        generic_reply = (
            f"Hello, I am an automated assistant. I understand you are experiencing an issue regarding your flight. "
            f"Please visit our website at britishairways.com or contact customer relations for assistance."
        )

        return TriageDecision(
            intent=intent,
            confidence_score=0.72,
            should_escalate_to_human=escalate,
            escalation_reason=reason,
            draft_reply=generic_reply,
            grounded_sources=[]
        )
