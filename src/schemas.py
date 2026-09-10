from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AirlineIntent(str, Enum):
    FLIGHT_DISRUPTION = "FLIGHT_DISRUPTION"
    BAGGAGE_SERVICES = "BAGGAGE_SERVICES"
    BOOKING_TICKETING = "BOOKING_TICKETING"
    CHECKIN_BOARDING = "CHECKIN_BOARDING"
    REFUNDS_COMPENSATION = "REFUNDS_COMPENSATION"
    LOYALTY_AVIOS = "LOYALTY_AVIOS"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"


class CustomerTweetRequest(BaseModel):
    tweet_text: str = Field(
        ..., 
        min_length=1,
        max_length=500,
        description="The incoming customer message/tweet text to be analyzed and triaged.",
        examples=["Hi @British_Airways, what is the maximum cabin bag size and weight allowance for Euro Traveller?"]
    )
    tweet_id: Optional[str] = Field(
        None, 
        description="Optional unique Twitter status ID or customer ticket reference.",
        examples=["tweet_115712_sample_01"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tweet_text": "Hi @British_Airways, what is the maximum cabin bag size and weight allowance for Euro Traveller?",
                    "tweet_id": "ba_tweet_001"
                }
            ]
        }
    }


class HistoricalResolution(BaseModel):
    tweet_id: str
    customer_issue: str
    agent_solution: str
    relevance_score: Optional[float] = None


class TriageDecision(BaseModel):
    intent: AirlineIntent = Field(
        ..., 
        description="The classified operational airline intent (one of 7 mutually exclusive categories)."
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence in intent classification (between 0.0 and 1.0)."
    )
    should_escalate_to_human: bool = Field(
        ..., 
        description="True if this message requires human staff intervention, False if safe to auto-handle."
    )
    escalation_reason: Optional[str] = Field(
        None, 
        description="The clear operational reason explaining why human escalation is needed, or None if auto-handled."
    )
    draft_reply: str = Field(
        ..., 
        description="The drafted customer reply grounded in British Airways past resolutions and brand tone."
    )
    grounded_sources: List[str] = Field(
        default_factory=list, 
        description="IDs of historical resolutions retrieved from the knowledge base."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "intent": "GENERAL_INQUIRY",
                "confidence_score": 0.98,
                "should_escalate_to_human": False,
                "escalation_reason": None,
                "draft_reply": "Hi there. In Euro Traveller, you are allowed one cabin bag (up to 56 x 45 x 25cm) plus one small personal item (up to 40 x 30 x 15cm), each weighing up to 23kg. You can find full details on ba.uk/baggage. Hope this helps! ^JM",
                "grounded_sources": [
                    "doc_129481_0",
                    "doc_109283_1"
                ]
            }
        }
    }


class JudgeEvaluation(BaseModel):
    groundedness_score: int = Field(..., ge=1, le=5, description="Is the reply grounded in real BA policy? (1-5)")
    brand_tone_score: int = Field(..., ge=1, le=5, description="Is the tone empathetic, professional, and BA-like? (1-5)")
    actionability_score: int = Field(..., ge=1, le=5, description="Does it give clear, useful next steps to the customer? (1-5)")
    safety_score: int = Field(..., ge=1, le=5, description="Does it avoid hallucinations, false promises, and protect PII? (1-5)")
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Average across the 4 criteria")
    explanation: str = Field(..., description="Brief explanation of the scores")


class GoldenEvaluationSample(BaseModel):
    sample_id: str
    customer_tweet: str
    true_intent: AirlineIntent
    true_should_escalate: bool
    true_escalation_reason: str
    historical_reference_reply: str
    human_quality_score: float = Field(default=5.0, ge=1.0, le=5.0)
