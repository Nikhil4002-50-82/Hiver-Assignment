"""
FastAPI Microservice for British Airways AI Support Agent.

Provides HTTP REST endpoints for real-time customer tweet triage,
intent classification, escalation decisions, and grounded reply drafting.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.schemas import CustomerTweetRequest, TriageDecision
from src.agent import BritishAirwaysAgent

# Initialize FastAPI application
app = FastAPI(
    title="British Airways AI Support Agent API",
    description="Automated triage, intent classification, and grounded resolution engine for @British_Airways",
    version="1.0.0"
)

# Enable CORS for frontend or dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize single agent instance
agent = BritishAirwaysAgent()


@app.get("/")
def read_root():
    """Welcome endpoint providing service overview and documentation link."""
    return {
        "service": "British Airways AI Support Agent API",
        "brand": "@British_Airways",
        "status": "operational",
        "interactive_docs_url": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint for container and service monitoring."""
    return {
        "status": "healthy",
        "gemini_api_connected": agent.is_api_active,
        "vector_store_records": agent.vector_store.count_indexed_records()
    }


@app.post("/api/v1/triage", response_model=TriageDecision)
def triage_customer_tweet(request: CustomerTweetRequest):
    """
    Main triage endpoint:
    - Analyzes incoming customer tweet
    - Classifies operational intent
    - Decides whether to auto-handle or escalate to human staff
    - Drafts an empathetic reply grounded in past British Airways resolutions
    """
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
