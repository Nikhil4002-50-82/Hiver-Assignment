
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from src.schemas import CustomerTweetRequest, TriageDecision
from src.agent import BritishAirwaysAgent

app = FastAPI(
    title="British Airways AI Support Agent API",
    description="""
Enterprise AI customer support microservice for **British Airways (`@British_Airways`)**:
* **Layer 1 (Interface)**: High-performance asynchronous REST API with strict Pydantic v2 data validation.
* **Layer 2 (Memory Vault)**: ChromaDB semantic search over 23,859 historical British Airways resolutions.
* **Layer 3 (Intent Classifier)**: Operational mapping into 7 mutually exclusive airline departments.
* **Layer 4 (Hybrid Triage)**: Deterministic regex/keyword guardrails for passenger safety, PII protection, and emergency escalation.
* **Layer 5 (Quality & Grounding)**: Empathetic response generation grounded in real airline precedents.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = BritishAirwaysAgent()

TRIAGE_EXAMPLES = {
    "policy_faq_auto_handle": {
        "summary": "1. Policy FAQ (Cabin Bag Allowance) - Auto-Handle",
        "description": "Routine informational inquiry about hand luggage dimensions and weights. Safe for autonomous resolution with zero PII.",
        "value": {
            "tweet_text": "Hi @British_Airways, what is the maximum cabin bag size and weight allowance for Euro Traveller?",
            "tweet_id": "tweet_faq_001"
        }
    },
    "lost_baggage_escalate": {
        "summary": "2. Lost Baggage on Arrival - Escalate to Human",
        "description": "Customer arrived at destination but luggage was not on the carousel. Mandatory escalation requiring a WorldTracer PIR record.",
        "value": {
            "tweet_text": "@British_Airways Landed at Edinburgh 3 hours ago from Gatwick and my suitcase never arrived on the carousel. Where is my bag??",
            "tweet_id": "tweet_bag_002"
        }
    },
    "flight_cancelled_stranded": {
        "summary": "3. Flight Disruption (Stranded Passenger) - Emergency Escalation",
        "description": "Active disruption with passenger stranded overnight at London Heathrow. High operational urgency requiring duty manager rebooking.",
        "value": {
            "tweet_text": "Thanks @British_Airways for cancelling BA1452 and letting me sleep on the cold floor of Heathrow Terminal 5 for my honeymoon!",
            "tweet_id": "tweet_disruption_003"
        }
    },
    "public_pnr_pii_risk": {
        "summary": "4. Public Booking Reference (PII Risk) - Security Escalation",
        "description": "Customer publicly tweeted 6-character PNR booking code (KL92X1). Immediate escalation to DM to prevent unauthorized itinerary hijacking.",
        "value": {
            "tweet_text": "Can someone at @British_Airways help change my seat to an aisle on booking ref KL92X1 for tomorrow?",
            "tweet_id": "tweet_pnr_004"
        }
    },
    "eu261_compensation_claim": {
        "summary": "5. Statutory EU261 Delay Compensation - Audit Escalation",
        "description": "Passenger claiming statutory financial compensation for a 5-hour delay. Requires flight log and air traffic audit by claims desk.",
        "value": {
            "tweet_text": "@British_Airways our flight from Nice was delayed 5 hours yesterday. Where do I submit my statutory EU261 compensation claim?",
            "tweet_id": "tweet_claim_005"
        }
    },
    "loyalty_avios_inquiry": {
        "summary": "6. Executive Club Avios & Tier Points - Account Escalation",
        "description": "Frequent flyer account inquiry regarding missing tier points. Requires private DM verification of 8-digit membership credentials.",
        "value": {
            "tweet_text": "@British_Airways My Executive Club tier points from flight BA178 to New York haven't posted yet. Can you check my Avios balance?",
            "tweet_id": "tweet_avios_006"
        }
    },
    "mobile_checkin_error": {
        "summary": "7. Mobile Check-in Glitch at Terminal Gate - Airport Escalation",
        "description": "Passenger unable to load boarding pass barcode at airport gate prior to departure. Requires ground services staff intervention.",
        "value": {
            "tweet_text": "@British_Airways The mobile app keeps crashing when I try to retrieve my boarding pass at Terminal 5 Gate B32!",
            "tweet_id": "tweet_checkin_007"
        }
    }
}



@app.get("/health", summary="Live Service Health Check")
def health_check():
    return {
        "status": "healthy",
        "gemini_api_connected": agent.is_api_active,
        "vector_store_records": agent.vector_store.count_indexed_records()
    }


@app.post(
    "/api/v1/triage", 
    response_model=TriageDecision,
    summary="Triage Customer Tweet",
    description="""
**Comprehensive Customer Tweet Triage & Grounded Resolution Endpoint**:

1. **Classification**: Maps unstructured tweet into 1 of 7 operational British Airways intents.
2. **Deterministic Guardrails**: Immediately intercepts PII leaks (6-char PNRs), stranded travelers, lost bags (WorldTracer PIR), and statutory claims (EU261).
3. **ChromaDB RAG**: Retrieves top-3 historically verified agent resolutions to ground replies in actual airline policies.
4. **Actionable Resolution**: Returns a structured decision with confidence score, escalation recommendation, justification, and pre-drafted empathetic reply.

*Select any pre-configured scenario from the **Examples dropdown** below to test immediately!*
    """,
    responses={
        200: {
            "description": "Successful triage analysis with structured operational routing and drafted reply.",
        },
        400: {
            "description": "Validation Error: tweet_text cannot be empty or whitespace.",
        },
        500: {
            "description": "Internal Agent Processing Error.",
        }
    }
)
def triage_customer_tweet(
    request: CustomerTweetRequest = Body(
        ...,
        openapi_examples=TRIAGE_EXAMPLES
    )
):
    if not request.tweet_text.strip():
        raise HTTPException(status_code=400, detail="tweet_text cannot be empty.")

    try:
        decision = agent.process_tweet(
            tweet_text=request.tweet_text,
            tweet_id=request.tweet_id
        )
        return decision
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Agent processing error: {str(error)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
