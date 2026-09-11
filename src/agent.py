import json
import re
from typing import Optional, List
from src.config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL
from src.schemas import (
    AirlineIntent, 
    CustomerTweetRequest, 
    TriageDecision, 
    HistoricalResolution
)
from src.vector_store import ResolutionVectorStore

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class BritishAirwaysAgent:
    def __init__(
        self, 
        api_key: str = GEMINI_API_KEY, 
        model_name: str = DEFAULT_GEMINI_MODEL,
        vector_store: Optional[ResolutionVectorStore] = None
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.vector_store = vector_store or ResolutionVectorStore()
        self.client = None

        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as error:
                print(f"[WARNING] Could not initialize Gemini Client: {error}")

    @property
    def is_api_active(self) -> bool:
        return self.client is not None

    def check_deterministic_guardrails(self, tweet_text: str) -> Optional[dict]:
        text_lower = tweet_text.lower()

        if any(w in text_lower for w in ["allowance", "hand luggage", "cabin bag", "pet in cabin", "what terminal", "baggage size", "bag size"]):
            return {
                "intent": AirlineIntent.GENERAL_INQUIRY,
                "should_escalate": False,
                "reason": None
            }

        if any(w in text_lower for w in ["lost bag", "damaged luggage", "suitcase was lost", "lost luggage", "missing bag", "carousel", "pir"]):
            return {
                "intent": AirlineIntent.BAGGAGE_SERVICES,
                "should_escalate": True,
                "reason": "Passenger baggage is missing or damaged; requires WorldTracer PIR record creation by baggage agent."
            }

        if any(w in text_lower for w in ["eu261", "eu 261", "compensation", "claim", "hotel bill", "food bill", "refund"]):
            return {
                "intent": AirlineIntent.REFUNDS_COMPENSATION,
                "should_escalate": True,
                "reason": "Customer is claiming cash compensation or statutory EU261 reimbursement; requires human case verification."
            }

        if any(w in text_lower for w in ["stranded", "stuck at terminal", "cancelled", "cancel", "delay", "divert", "missed connection"]):
            return {
                "intent": AirlineIntent.FLIGHT_DISRUPTION,
                "should_escalate": True,
                "reason": "Customer experiencing active flight disruption or is stranded in transit; requires priority rebooking."
            }

        pnr_match = re.search(r"\b[A-Z0-9]{6}\b", tweet_text.upper())
        if pnr_match and any(w in text_lower for w in ["booking", "ref", "pnr", "flight"]):
            return {
                "intent": AirlineIntent.BOOKING_TICKETING,
                "should_escalate": True,
                "reason": "Customer shared a booking reference publicly; requires private DM handling to protect passenger privacy."
            }

        return None

    def classify_intent_offline(self, tweet_text: str) -> AirlineIntent:
        text_lower = tweet_text.lower()
        if any(w in text_lower for w in ["bag", "luggage", "suitcase", "carousel", "pir"]):
            return AirlineIntent.BAGGAGE_SERVICES
        elif any(w in text_lower for w in ["compensation", "eu261", "eu 261", "claim", "refund", "hotel bill", "food bill", "expenses"]):
            return AirlineIntent.REFUNDS_COMPENSATION
        elif any(w in text_lower for w in ["cancel", "delay", "divert", "stranded", "missed", "stuck at", "strike"]):
            return AirlineIntent.FLIGHT_DISRUPTION
        elif any(w in text_lower for w in ["check in", "check-in", "boarding pass", "barcode", "terminal"]):
            return AirlineIntent.CHECKIN_BOARDING
        elif any(w in text_lower for w in ["avios", "executive club", "tier points", "gold card", "silver card", "bronze", "baec"]):
            return AirlineIntent.LOYALTY_AVIOS
        elif any(w in text_lower for w in ["booking", "ticket", "upgrade", "seat", "name change", "change flight", "pnr", "reference"]):
            return AirlineIntent.BOOKING_TICKETING
        else:
            return AirlineIntent.GENERAL_INQUIRY

    def build_system_prompt(self, retrieved_resolutions: List[HistoricalResolution]) -> str:
        context_blocks = []
        for idx, res in enumerate(retrieved_resolutions, 1):
            context_blocks.append(
                f"[Past Case {idx}]\n"
                f"Customer Tweet: {res.customer_issue}\n"
                f"BA Agent Resolution: {res.agent_solution}"
            )
        historical_context = "\n\n".join(context_blocks) if context_blocks else "No direct historical matches found."

        prompt = f"""You are the official British Airways Customer Support AI Agent on Twitter (@British_Airways).
Your mission is to classify customer intent, decide on human escalation, and draft an empathetic, brand-aligned reply.

British Airways Brand Tone Guidelines:
- Polite, calm, empathetic, and reassuring (quintessentially British customer service).
- Never make false promises or confirm flight changes publicly.
- For private actions (seat changes, booking access, compensation claims, baggage tracing), instruct the customer to send a Direct Message (DM) with their 6-character booking reference (PNR).
- Always end responses with British Airways agent initials (e.g., ^JM, ^Sarah, ^SB).

Here are real historical British Airways resolutions for similar customer issues:
{historical_context}

Available Operational Intents:
1. FLIGHT_DISRUPTION (Delays, cancellations, missed connections, strikes)
2. BAGGAGE_SERVICES (Lost, delayed, damaged luggage, WorldTracer PIR)
3. BOOKING_TICKETING (Seat selection, date change, upgrades, name errors)
4. CHECKIN_BOARDING (Check-in failures, mobile boarding pass, terminal info)
5. REFUNDS_COMPENSATION (EU261 delay claims, hotel/meal expenses, refunds)
6. LOYALTY_AVIOS (Executive Club account, missing Avios or tier points)
7. GENERAL_INQUIRY (Baggage size policy, pets, onboard wifi, compliments)

Escalation Rules:
- ESCALATE (should_escalate_to_human = true) if:
  * Passenger is stranded, in transit, or cancelled today.
  * Customer requires PII access (booking reference, ticket changes, refunds, luggage tracing).
  * Passenger is extremely distressed, angry, or claiming compensation.
  * You are not completely confident in auto-handling.
- AUTO-HANDLE (should_escalate_to_human = false) only if:
  * The question is purely informational (e.g. hand luggage dimensions, check-in opening times, compliments).

Output must strictly conform to JSON matching the required schema.
"""
        return prompt

    def process_tweet(self, tweet_text: str, tweet_id: Optional[str] = None) -> TriageDecision:
        retrieved_resolutions = self.vector_store.search_similar_resolutions(tweet_text, top_k=3)
        retrieved_ids = [res.tweet_id for res in retrieved_resolutions]

        guardrail_result = self.check_deterministic_guardrails(tweet_text)

        if self.is_api_active:
            try:
                system_prompt = self.build_system_prompt(retrieved_resolutions)
                user_message = f"Incoming Customer Tweet: \"{tweet_text}\"\n\nProduce your classification, escalation decision, and draft reply."

                candidate_models = [self.model_name]
                for fallback_m in ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]:
                    if fallback_m not in candidate_models:
                        candidate_models.append(fallback_m)

                response = None
                for model_candidate in candidate_models:
                    try:
                        response = self.client.models.generate_content(
                            model=model_candidate,
                            contents=user_message,
                            config=types.GenerateContentConfig(
                                system_instruction=system_prompt,
                                response_mime_type="application/json",
                                response_schema=TriageDecision,
                                temperature=0.2,
                            ),
                        )
                        if response and response.text:
                            break
                    except Exception:
                        continue

                if not response:
                    raise RuntimeError("All candidate flash models temporarily unavailable.")

                data = json.loads(response.text)
                
                if guardrail_result:
                    data["should_escalate_to_human"] = guardrail_result["should_escalate"]
                    if guardrail_result["reason"]:
                        data["escalation_reason"] = guardrail_result["reason"]
                    data["intent"] = guardrail_result["intent"].value

                data["grounded_sources"] = retrieved_ids
                return TriageDecision(**data)

            except Exception as error:
                print(f"[WARNING] Gemini generation error: {error}. Using grounded fallback.")

        intent = self.classify_intent_offline(tweet_text)
        
        if guardrail_result:
            should_escalate = guardrail_result["should_escalate"]
            reason = guardrail_result["reason"]
        else:
            should_escalate = intent != AirlineIntent.GENERAL_INQUIRY
            reason = "Operational inquiry requiring customer verification." if should_escalate else None

        if retrieved_resolutions:
            best_res = retrieved_resolutions[0]
            draft = best_res.agent_solution
            if "^" not in draft:
                draft += " ^JM"
        else:
            draft = (
                "Hi there, we're sorry for the inconvenience caused. "
                "Please send us a Direct Message with your 6-character booking reference and full details "
                "so our team can look into this for you right away. ^JM"
            )

        return TriageDecision(
            intent=intent,
            confidence_score=0.92,
            should_escalate_to_human=should_escalate,
            escalation_reason=reason if should_escalate else None,
            draft_reply=draft,
            grounded_sources=retrieved_ids
        )
