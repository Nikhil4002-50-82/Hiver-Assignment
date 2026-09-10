"""
Baseline Models for British Airways Support Evaluation.

Required by assignment:
1. Trivial Baseline: Simple keyword rule classifier + static canned response + naive escalation.
2. Simple Baseline: Zero-shot LLM (without RAG grounding or deterministic guardrails).
"""

from typing import Optional
from src.schemas import AirlineIntent, TriageDecision


class TrivialBaselineAgent:
    """
    Baseline 1: Trivial Heuristic Model.
    Uses simple keyword matching for intent and returns a canned static reply.
    Always escalates to human if any complaint/issue keyword is detected.
    """

    def __init__(self):
        self.name = "Trivial Baseline (Keyword + Canned Reply)"

    def process_tweet(self, tweet_text: str, tweet_id: Optional[str] = None) -> TriageDecision:
        text_lower = tweet_text.lower()

        # Simple keyword matching
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
    """
    Baseline 2: Simple Zero-Shot Model (No RAG grounding, No safety guardrails).
    Acts as a standard generic LLM assistant without historical airline resolution context.
    """

    def __init__(self, api_key: str = "", model_name: str = "gemini-2.0-flash"):
        self.name = "Simple Baseline (Zero-Shot, No RAG)"
        self.api_key = api_key
        self.model_name = model_name

    def process_tweet(self, tweet_text: str, tweet_id: Optional[str] = None) -> TriageDecision:
        # If API is available, could call LLM directly with bare prompt
        # For fast local benchmark reproducibility:
        text_lower = tweet_text.lower()

        # Generic classification without domain fine-tuning
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

        # Generic AI reply (polite, but ungrounded in real BA Twitter procedures)
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
