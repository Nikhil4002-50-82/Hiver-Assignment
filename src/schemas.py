from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AirlineIntent(str, Enum):
    """The 7 main operational categories of customer requests for British Airways."""
    FLIGHT_DISRUPTION = "FLIGHT_DISRUPTION"          # Flight delays, cancellations, missed connections, strikes
    BAGGAGE_SERVICES = "BAGGAGE_SERVICES"            # Lost, delayed, or damaged luggage, WorldTracer PIR info
    BOOKING_TICKETING = "BOOKING_TICKETING"          # Seat selection, date changes, upgrades, name corrections
    CHECKIN_BOARDING = "CHECKIN_BOARDING"            # Online check-in issues, boarding pass retrieval, terminal info
    REFUNDS_COMPENSATION = "REFUNDS_COMPENSATION"    # EU261 statutory delay compensation, cancelled ticket refunds
    LOYALTY_AVIOS = "LOYALTY_AVIOS"                  # Executive Club account issues, missing Avios or tier points
    GENERAL_INQUIRY = "GENERAL_INQUIRY"              # Baggage allowance rules, pet travel, lounge access, feedback


class CustomerTweetRequest(BaseModel):
    """Incoming tweet from a customer."""
    tweet_text: str = Field(..., description="The text of the incoming customer tweet")
    tweet_id: Optional[str] = Field(None, description="Optional ID of the customer tweet")


class HistoricalResolution(BaseModel):
    """A past resolved customer interaction by a British Airways agent."""
    tweet_id: str
    customer_issue: str
    agent_solution: str
    relevance_score: Optional[float] = None


class TriageDecision(BaseModel):
    """The final structured decision and draft produced by the AI Agent."""
    intent: AirlineIntent = Field(
        ..., 
        description="The classified customer intent"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence in intent classification (between 0.0 and 1.0)"
    )
    should_escalate_to_human: bool = Field(
        ..., 
        description="True if this message requires human staff intervention, False if safe to auto-handle"
    )
    escalation_reason: Optional[str] = Field(
        None, 
        description="The clear reason explaining why human escalation is needed, or None if auto-handled"
    )
    draft_reply: str = Field(
        ..., 
        description="The drafted customer reply grounded in British Airways past resolutions and tone"
    )
    grounded_sources: List[str] = Field(
        default_factory=list, 
        description="IDs of historical resolutions retrieved from the knowledge base"
    )


class JudgeEvaluation(BaseModel):
    """Rubric evaluation of a draft reply scored by the LLM-as-a-Judge."""
    groundedness_score: int = Field(..., ge=1, le=5, description="Is the reply grounded in real BA policy? (1-5)")
    brand_tone_score: int = Field(..., ge=1, le=5, description="Is the tone empathetic, professional, and BA-like? (1-5)")
    actionability_score: int = Field(..., ge=1, le=5, description="Does it give clear, useful next steps to the customer? (1-5)")
    safety_score: int = Field(..., ge=1, le=5, description="Does it avoid hallucinations, false promises, and protect PII? (1-5)")
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Average across the 4 criteria")
    explanation: str = Field(..., description="Brief explanation of the scores")


class GoldenEvaluationSample(BaseModel):
    """A single hand-labelled example in our golden test set."""
    sample_id: str
    customer_tweet: str
    true_intent: AirlineIntent
    true_should_escalate: bool
    true_escalation_reason: str
    historical_reference_reply: str
    human_quality_score: float = Field(default=5.0, ge=1.0, le=5.0)
