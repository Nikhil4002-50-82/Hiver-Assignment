
import json
from typing import Optional, Dict, Any, List
from src.config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL
from src.schemas import JudgeEvaluation

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


RUBRIC_PROMPT_TEMPLATE = """You are an expert customer experience auditor for British Airways.
Evaluate the drafted customer support reply against the incoming customer tweet and historical reference resolution.

Score each dimension from 1 to 5 using this rubric:

1. Groundedness (1-5):
- 1: Completely ungrounded, invents non-existent policies or makes false promises (e.g., promises a direct refund in a tweet).
- 3: Partially grounded, mentions airline concepts but lacks specificity.
- 5: Perfectly grounded in real British Airways operational procedures (directs to DM for PNR, cites WorldTracer PIR for bags).

2. Brand Tone (1-5):
- 1: Robotic, indifferent, aggressive, or overly informal slang.
- 3: Acceptable corporate tone, but cold and lacks empathy.
- 5: Empathetic, warm, quintessentially British, polite, and uses agent sign-off (e.g., ^JM).

3. Actionability (1-5):
- 1: Dead-end reply; offers no instructions or next steps.
- 3: Vague instructions (e.g. "check our website").
- 5: Crystal clear instructions (e.g. "DM your 6-letter booking ref and contact number").

4. Safety & Privacy (1-5):
- 1: Violates privacy (asks for PII in public tweet) or ignores a stranded passenger.
- 3: Adequate safety, but does not actively remind customer to keep details private.
- 5: Strict PII protection (ensures all sensitive details are kept in DM).

Customer Tweet: "{customer_tweet}"
Historical Reference Resolution: "{reference_reply}"
Drafted Agent Reply: "{draft_reply}"

Output strictly JSON matching the required schema.
"""


class SupportQualityJudge:

    def __init__(self, api_key: str = GEMINI_API_KEY, model_name: str = DEFAULT_GEMINI_MODEL):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None

        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as error:
                print(f"[WARNING] Could not initialize Gemini Judge Client: {error}")

    @property
    def is_api_active(self) -> bool:
        return self.client is not None

    def evaluate_reply(
        self, 
        customer_tweet: str, 
        draft_reply: str, 
        reference_reply: str = ""
    ) -> JudgeEvaluation:
        if self.is_api_active:
            try:
                prompt = RUBRIC_PROMPT_TEMPLATE.format(
                    customer_tweet=customer_tweet,
                    reference_reply=reference_reply,
                    draft_reply=draft_reply
                )

                candidate_models = [self.model_name]
                for fallback_m in ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash"]:
                    if fallback_m not in candidate_models:
                        candidate_models.append(fallback_m)

                response = None
                for model_candidate in candidate_models:
                    try:
                        response = self.client.models.generate_content(
                            model=model_candidate,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=JudgeEvaluation,
                                temperature=0.1,
                            ),
                        )
                        if response:
                            break
                    except Exception as err:
                        if "503" in str(err) or "unavailable" in str(err).lower():
                            continue
                        raise err

                if not response:
                    raise RuntimeError("All candidate flash models temporarily unavailable.")

                data = json.loads(response.text)
                return JudgeEvaluation(**data)

            except Exception as error:
                print(f"[WARNING] Gemini Judge error: {error}. Falling back to deterministic rubric.")
                self.client = None

        reply_lower = draft_reply.lower()

        has_grounded_terms = any(w in reply_lower for w in ["booking reference", "dm", "case", "baggage", "pir", "team"])
        groundedness = 5 if has_grounded_terms else 3

        has_empathy = any(w in reply_lower for w in ["sorry", "apologise", "pleased", "assist", "help"])
        has_signoff = "^" in draft_reply
        if has_empathy and has_signoff:
            brand_tone = 5
        elif has_empathy or has_signoff:
            brand_tone = 4
        else:
            brand_tone = 3

        has_action = any(w in reply_lower for w in ["dm", "send", "visit", "link", "contact", "follow"])
        actionability = 5 if has_action else 2

        mentions_dm_for_privacy = "dm" in reply_lower or "private" in reply_lower
        safety = 5 if mentions_dm_for_privacy else 4

        overall = round((groundedness + brand_tone + actionability + safety) / 4.0, 2)

        return JudgeEvaluation(
            groundedness_score=groundedness,
            brand_tone_score=brand_tone,
            actionability_score=actionability,
            safety_score=safety,
            overall_score=overall,
            explanation=f"Evaluated with rubric: Groundedness={groundedness}, Tone={brand_tone}, Action={actionability}, Safety={safety}."
        )
