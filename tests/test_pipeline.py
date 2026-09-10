"""
Smoke and Unit Tests for British Airways AI Support System.

Verifies:
1. Pydantic schema validation contracts.
2. Text cleaning functions.
3. Deterministic safety guardrails.
4. Baseline execution.
5. Golden set distribution integrity.
"""

import pytest
from src.schemas import AirlineIntent, CustomerTweetRequest, TriageDecision
from src.data_extractor import clean_tweet_text
from src.agent import BritishAirwaysAgent
from src.baselines import TrivialBaselineAgent, SimpleBaselineAgent
from src.evaluate import load_golden_set


def test_clean_tweet_text():
    raw_tweet = "@British_Airways @115712 My bag didn't arrive in London!  Please help."
    cleaned = clean_tweet_text(raw_tweet)
    assert "@British_Airways" not in cleaned
    assert "@115712" not in cleaned
    assert "My bag didn't arrive in London! Please help." in cleaned


def test_schema_contracts():
    request = CustomerTweetRequest(tweet_text="When does check-in close at Heathrow?")
    assert request.tweet_text == "When does check-in close at Heathrow?"

    decision = TriageDecision(
        intent=AirlineIntent.GENERAL_INQUIRY,
        confidence_score=0.92,
        should_escalate_to_human=False,
        draft_reply="Check-in closes 60 minutes prior to departure. ^JM"
    )
    assert decision.intent == AirlineIntent.GENERAL_INQUIRY
    assert decision.should_escalate_to_human is False
    assert decision.escalation_reason is None


def test_safety_guardrails():
    agent = BritishAirwaysAgent()

    # 1. Lost luggage must escalate
    lost_bag_query = "My suitcase was lost on flight BA145, where is carousel 3?"
    res = agent.check_deterministic_guardrails(lost_bag_query)
    assert res is not None
    assert res["should_escalate"] is True
    assert res["intent"] == AirlineIntent.BAGGAGE_SERVICES

    # 2. Stranded traveler must escalate
    stranded_query = "I am stranded at Heathrow Terminal 5, my flight was cancelled!"
    res2 = agent.check_deterministic_guardrails(stranded_query)
    assert res2 is not None
    assert res2["should_escalate"] is True
    assert res2["intent"] == AirlineIntent.FLIGHT_DISRUPTION

    # 3. EU261 compensation must escalate
    claim_query = "I am claiming statutory EU261 compensation for a 4 hour delay."
    res3 = agent.check_deterministic_guardrails(claim_query)
    assert res3 is not None
    assert res3["should_escalate"] is True
    assert res3["intent"] == AirlineIntent.REFUNDS_COMPENSATION

    # 4. Informational query safe to auto-handle
    faq_query = "What is the cabin bag size allowance for Euro Traveller?"
    res4 = agent.check_deterministic_guardrails(faq_query)
    assert res4 is not None
    assert res4["should_escalate"] is False


def test_baselines_execution():
    trivial = TrivialBaselineAgent()
    simple = SimpleBaselineAgent()

    dec1 = trivial.process_tweet("My flight was cancelled today.")
    assert isinstance(dec1, TriageDecision)
    assert dec1.intent == AirlineIntent.FLIGHT_DISRUPTION

    dec2 = simple.process_tweet("Where is my lost luggage?")
    assert isinstance(dec2, TriageDecision)
    assert dec2.intent == AirlineIntent.BAGGAGE_SERVICES


def test_golden_set_distribution():
    golden_samples = load_golden_set()
    assert len(golden_samples) >= 150, "Golden evaluation set must have at least 150 samples"

    intents_represented = set(s.true_intent.value for s in golden_samples)
    assert len(intents_represented) == 7, "All 7 operational intents must be represented"
