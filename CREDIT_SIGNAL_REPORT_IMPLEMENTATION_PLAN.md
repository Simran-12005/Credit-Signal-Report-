# Credit Signal Report — Implementation Plan

## What we're building

Input a customer's **GSTIN** → get a **credit signal report** that helps a supplier decide:
*"Should I give this customer 30–60 day credit?"*

**Strategy:** First **collect data** across several phases. Once we have enough clean, labelled data, **train AI models** on it to predict credit risk.

**Tech:** FastAPI · PostgreSQL (`csr_` tables) · Celery · Router→Service→DAO→Model. Lives inside `marketing-service`.

---

# Part A — Collect the Data

Goal of Part A: build a clean, growing dataset of signals + real outcomes (who paid on time, who didn't). This dataset is what we train models on later.

### Phase 0 — Foundation
Set up the skeleton.
- DB tables, API, auth.
- `POST /credit-signal/reports` (send GSTIN), `GET .../{id}` (read report).
- Validate GSTIN; each supplier sees only its own data.

➡️ Pipeline works end-to-end.

### Phase 1 — Collect payment history *(start here)*
Capture the supplier's own orders + payments. **Free, and our most valuable data.**
- Store: order count, amounts, due date, paid date, delays, bounces.
- **Manual simulator UI (this is a standalone system, so no real billing to pull from yet):**
  a screen to add/edit buyers and their orders, mark invoices as paid (with a paid date),
  flag bounces, and bulk-load sample data — so we can simulate realistic payment behaviour
  and generate the labelled outcomes the models need.
- Also support CSV upload for bulk entry.

➡️ This becomes our **outcome label** — who actually pays well.

### Phase 2 — Collect GST data
Connect one GST provider (Clear / Karza / Signzy).
- Business profile: name, registration date, type, state.
- Compliance: filing consistency, missed filings, cancellation/suspension.
- Cache + log every paid API call.

➡️ Rich compliance features per business.

### Phase 3 — Collect MCA + legal data
- **Companies:** age, directors, loans/charges, strike-off, filings (MCA).
- **Legal:** insolvency + recovery cases (NJDG / IBBI).

➡️ Deeper features, especially for companies.

### Phase 4 — Store as clean feature dataset
Turn everything collected into one structured, ML-ready dataset.
- One row per business: all signals as features + payment outcome as label.
- Versioned, with `as_of_date` per signal.
- Simple rule-based report meanwhile (weighted signals) so the product is usable while data grows.

➡️ A labelled dataset ready for training.

---

# Part B — Train AI Models on the Data

Goal of Part B: once enough data is collected, train models to predict credit risk and improve over time.

### Phase 5 — First model
Train a baseline model on the Phase 4 dataset.
- Predict likelihood of on-time payment / default risk.
- Compare against the rule-based score; keep whichever is better.
- Track accuracy, precision/recall.

➡️ First AI-driven risk score.

### Phase 6 — Serve + explain predictions
Put the model behind the report.
- Report shows the model score **plus** the top signals that drove it (explainable).
- Log predictions vs real outcomes for continuous evaluation.

➡️ Suppliers get an AI score they can trust and understand.

### Phase 7 — Retrain + improve
Close the loop.
- Periodically retrain as more payment outcomes arrive.
- Add the **payment network** signal: anonymized data across many suppliers
  (*"120 suppliers reported this buyer, avg delay 22 days"*) — needs legal sign-off.

➡️ Model keeps getting smarter as data grows.

---

## Always-on rules
- Cache + log every paid API call (control cost).
- Keep raw signals + sources — needed to retrain later.
- Suppliers only see their own data.
- Missing data never breaks the report.

## Why this order
Collect the free, most-trusted data first (Phase 1), then external data (2–3), build a clean labelled dataset (4) — only then train models (5–7). No model is trained until we have real outcomes to learn from.
