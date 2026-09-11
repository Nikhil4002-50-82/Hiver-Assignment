# Engineering Decision Log: British Airways AI Support Agent

A plain list of 12 non-obvious engineering and architectural decisions made during development, along with their rationale.

---

### 1. Direct Python + Google GenAI SDK over Heavy Frameworks (LangChain / LlamaIndex)
* **Decision**: Implemented the agent orchestration in clean, modular Python using the official `google-genai` SDK and Pydantic v2, rather than wrapping it in LangChain or LlamaIndex.
* **Why**: Heavy frameworks introduce multi-layered abstraction bloat, unpredictable prompt rewriting, and brittle debugging traces. In an SDE interview where candidates must modify and explain their code live, direct SDK calls are transparent, fast, and 100% controllable.

---

### 2. Conversation Pairing Preprocessing from 1.5 GB to 6.5 MB
* **Decision**: Extracted and paired parent customer tweets with actual British Airways replies offline into `ba_conversation_pairs.csv` (6.5 MB, ~23,800 pairs), discarding the 1.5 GB raw `twcs.csv`.
* **Why**: Loading the raw 3M-row dataset repeatedly exhausts RAM and causes cold-start latency. Slicing down to genuine `@British_Airways` conversation pairs enables reviewers to reproduce all results in under 5 minutes without memory bottlenecks.

---

### 3. Hybrid Triage: Deterministic Safety Guardrails + Semantic LLM Reasoning
* **Decision**: Paired probabilistic LLM triage with hard, deterministic policy guardrails for safety-critical airline scenarios (lost luggage, statutory EU261 claims, stranded travelers, PNR in public).
* **Why**: High-stakes aviation customer support cannot rely solely on probabilistic LLM "vibes". If a passenger is stranded at Heathrow or needs a WorldTracer PIR baggage reference, policy **mandates** human escalation regardless of model confidence.

---

### 4. Asymmetric Indexing in Vector Database
* **Decision**: In ChromaDB, we embedded the **historical customer problem text** as the indexed document, while storing the **BA agent resolution** as metadata.
* **Why**: An incoming customer tweet shares semantic similarity with *past customer inquiries*, not past agent replies. Matching customer query $\rightarrow$ past customer query retrieves far more accurate resolution pairs than query $\rightarrow$ agent text.

---

### 5. Prioritizing Escalation Recall over Precision
* **Decision**: Configured the triage engine to optimize for **Recall ($\ge 95\%$)** rather than maximizing Precision on human escalation.
* **Why**: In aviation, a False Negative (the AI auto-handling an issue when a customer was actually stranded or missing bags) results in severe customer harm, regulatory fines, and reputational damage. A False Positive simply results in a human agent verifying an easy ticket.

---

### 6. PNR (Booking Reference) Redaction & Immediate DM Routing
* **Decision**: Implemented regex detection for 6-character alphanumeric booking codes (PNRs). Any tweet containing a PNR triggers immediate escalation and guidance to move to Twitter DM.
* **Why**: Customers frequently post sensitive booking references publicly, exposing their full name, itinerary, and e-ticket numbers to identity theft. An enterprise airline agent must actively enforce privacy compliance.

---

### 7. Dual-Mode Embeddings (Gemini API with Local Fallback)
* **Decision**: Supported Google `gemini-embedding-2` when an API key is present, with an automatic fallback to ChromaDB's local sentence embeddings (`all-MiniLM-L6-v2`).
* **Why**: Guarantees that take-home evaluators can clone the repository, run `pytest` or `evaluate.py`, and inspect headline benchmarks even if they don't have an active Gemini API key configured in `.env`.

---

### 8. 7 Operational Intents Instead of Fine-Grained 77 Classes
* **Decision**: Designed a 7-intent taxonomy (`FLIGHT_DISRUPTION`, `BAGGAGE_SERVICES`, `BOOKING_TICKETING`, `CHECKIN_BOARDING`, `REFUNDS_COMPENSATION`, `LOYALTY_AVIOS`, `GENERAL_INQUIRY`) rather than deep hierarchical sub-intents (like Banking77).
* **Why**: Twitter messages are constrained and noisy. A 7-intent taxonomy mirrors real airline operational dispatch desks (baggage desk, rebooking desk, customer relations) with over 90% classification accuracy, avoiding boundary ambiguity.

---

### 9. Measuring Human-Judge Agreement via Cohen's Kappa ($\kappa$)
* **Decision**: Used Cohen's Kappa rather than raw percentage agreement to validate the LLM-as-a-Judge against human ratings.
* **Why**: Percentage agreement fails to account for agreement occurring purely by chance (especially on skewed 1-5 rating scales). Cohen's Kappa is the industry standard for inter-rater reliability.

---

### 10. Strict Schema Enforcement via Pydantic v2 JSON Schema Mode
* **Decision**: Used Gemini's native `response_schema` parameter typed to a Pydantic `TriageDecision` model.
* **Why**: Traditional prompt engineering ("Please return valid JSON") frequently results in markdown backticks or malformed JSON syntax. Native schema enforcement guarantees $100\%$ type-safe deserialization without regex workarounds.

---

### 11. Decoupled Architecture Serving Both CLI and FastAPI
* **Decision**: Isolated `BritishAirwaysAgent` as a standalone engine that powers both `evaluate.py` (CLI benchmark harness) and `src/api.py` (FastAPI REST service).
* **Why**: Shows software engineering maturity. The take-home reviewer can inspect offline batch evaluation and immediately test the same agent in an interactive Swagger UI (`http://localhost:8000/docs`).

---

### 12. Stratified Golden Set with 20% Hard Adversarial Edge Cases
* **Decision**: Intentionally included 40 hard edge cases (sarcasm, passive aggression, mixed multi-issue complaints) in the 210-sample golden set.
* **Why**: Real customer tweets are rarely polite, clean FAQs. Including challenging cases prevents inflated vanity metrics and provides genuine failure modes for critical analysis.
