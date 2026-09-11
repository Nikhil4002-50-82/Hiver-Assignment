# Golden Evaluation Set: Sampling & Labelling Methodology

**Target Brand**: British Airways (`@British_Airways`)  
**Golden Set Size**: 210 Hand-Curated and Verified Examples  
**Dataset Source**: Kaggle Customer Support on Twitter (`thoughtvector/customer-support-on-twitter`)

---

## 1. Objective of the Golden Set

In an airline customer support setting, evaluation sets scraped purely with automated heuristics contain noisy labels, ambiguous intent overlap, and poor human triage ground truth. 

To prove our AI agent is trustworthy for production, we built a pristine **Golden Evaluation Set of 210 examples**, hand-labeled with:
1. **True Operational Intent** (one of 7 mutually exclusive airline categories)
2. **True Escalation Decision** (`True` for human agent required, `False` for safe auto-handle)
3. **Explicit Escalation Rationale** (the operational business justification)
4. **Historical Reference Reply** (the real verified British Airways Twitter resolution)
5. **Human Quality Benchmark Score** (1 to 5 scale, used to evaluate human-judge agreement via Cohen's Kappa)

---

## 2. Sampling Strategy & Stratification

### A. Stratified Intent Distribution
To avoid representation bias (where flight cancellations dominate all data), we sampled an exactly balanced 30 cases across all 7 operational buckets:

| Intent Category | Target Count | % of Golden Set | Description |
|---|---|---|---|
| **FLIGHT_DISRUPTION** | 30 | 14.3% | Cancellations, delays, missed connections, diversion, weather |
| **BAGGAGE_SERVICES** | 30 | 14.3% | Delayed bags, damaged luggage, WorldTracer PIR tracing |
| **BOOKING_TICKETING** | 30 | 14.3% | Seat assignments, name spellings, date rebooking, upgrades |
| **CHECKIN_BOARDING** | 30 | 14.3% | App check-in failure, boarding pass barcodes, terminal changes |
| **REFUNDS_COMPENSATION** | 30 | 14.3% | EU261 statutory delay claims, hotel expense reimbursement |
| **LOYALTY_AVIOS** | 30 | 14.3% | Executive Club password reset, missing Avios points |
| **GENERAL_INQUIRY** | 30 | 14.3% | Hand baggage allowances, pet policy, lounge rules, compliments |
| **Total** | **210** | **100%** | |

### B. Triage Distribution (Auto-Handle vs. Escalate)
* **Escalate to Human (`True`)**: 61.4% (129 samples)  
  *Justification*: Airline customer support on Twitter is heavily operational. Most passengers tweet because an automated system failed or they need urgent manual intervention requiring their 6-character Booking Reference (PNR).
* **Safe to Auto-Handle (`False`)**: 38.6% (81 samples)  
  *Justification*: Questions regarding baggage weight limits, pet travel guidelines, check-in opening windows, compliments, and standard policy FAQs.

---

## 3. Stratified Difficulty & Edge Cases

To prevent inflated headline metrics from testing only simple "happy paths", the golden set is stratified into three difficulty tiers:

1. **Tier 1: Direct / Single-Intent (~45% - 95 samples)**
   * Clear, unambiguous customer statements.
   * *Example*: *"What is the hand luggage allowance for a flight from LHR to JFK?"* $\rightarrow$ `GENERAL_INQUIRY`, Auto-handle.

2. **Tier 2: High-Emotion & Urgent (~35% - 73 samples)**
   * Passengers in active distress, stranded at airports, or expressing extreme anger.
   * *Example*: *"My connection to Delhi was cancelled, I've been waiting at Terminal 5 for 6 hours with no voucher or hotel. Disgraceful!"* $\rightarrow$ `FLIGHT_DISRUPTION`, Escalate.

3. **Tier 3: Complex Edge Cases & Ambiguity (~20% - 42 samples)**
   * **Multi-Intent**: Tweets combining two problems (e.g., flight delayed AND luggage missing). Labelled by primary operational urgency.
   * **Sarcasm / Passive Aggression**: *"Thanks British Airways for letting me spend my anniversary sleeping on the floor of Heathrow."* (Requires detecting disruption rather than genuine gratitude).
   * **Incomplete Context**: *"Can you fix this now? It's broken."* (Requires detecting low confidence / asking for clarification).
   * **PII in Public Tweets**: Customers dangerously posting their 6-character PNR or phone numbers publicly (Requires urgent escalation and guidance to delete public tweet).

---

## 4. Labelling Guidelines & Escalation Criteria

An example is labelled `should_escalate_to_human = True` if:
* Resolution requires accessing passenger PII, PNR booking reference, or ticketing systems via private DM.
* The customer is actively stranded or facing flight disruption within 24 hours.
* The customer is requesting financial compensation (EU261, cash refunds).
* The customer is reporting lost or damaged baggage requiring a WorldTracer PIR file reference.

An example is labelled `should_escalate_to_human = False` if:
* The query can be fully and accurately answered using static published airline policies (baggage dimensions, check-in opening hours, pet policies, lounge access).
* The customer is offering compliments, general feedback, or simple acknowledgment without an open issue.
