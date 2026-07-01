# Credit Signal Report

Standalone app that turns a **buyer's GSTIN** into a **credit signal report**, helping a
supplier decide whether to extend 30–60 day credit. This is **Part A — data collection**
(no AI yet). See [CREDIT_SIGNAL_REPORT_IMPLEMENTATION_PLAN.md](CREDIT_SIGNAL_REPORT_IMPLEMENTATION_PLAN.md).

- **Stack:** FastAPI · PostgreSQL (`csr_` tables) · SQLAlchemy async · Router→Service→DAO→Model
- **Auth:** per-supplier API keys (`X-API-Key` header). Suppliers only ever see their own data.
- **GST provider:** swappable `GstProvider` interface. `mock` (default, offline) or `perfios`
  (real sandbox — 10,000+ free credits, same stack as Karza). See
  [GST_PROVIDER_RESEARCH.md](GST_PROVIDER_RESEARCH.md).
- **MCA + legal provider:** swappable `McaProvider` interface. `mock` (default, offline) today;
  real providers (MCA21 aggregators + NJDG/IBBI) drop in behind the same interface.

## Status

**Part A (data collection) is complete: Phases 0–4.** Part B (AI models, Phases 5–7) is not started.

| Phase | What | State |
|---|---|---|
| 0 | Foundation: reports, auth, GSTIN validation | ✅ |
| 1 | Payment history (the outcome label) + simulator UI | ✅ |
| 2 | GST data with cache + cost log | ✅ |
| 3 | MCA + legal data (company / directors / charges / insolvency / recovery) | ✅ |
| 4 | Clean feature dataset + rule-based credit score | ✅ |

### Phase 0 — Reports
Send a GSTIN → validated → GST identity + compliance fetched from the provider → stored → readable.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/credit-signal/reports` | Create a report from a `{ "gstin": "..." }` body |
| `GET`  | `/credit-signal/reports/{id}` | Read one of your reports |
| `GET`  | `/credit-signal/reports` | List your reports |
| `GET`  | `/health` | Liveness + active provider |

### Phase 1 — Payment history (the outcome label)
Record buyers + their orders, mark paid / flag bounces, and read derived payment-behaviour
signals. There's a **simulator UI at `/simulator`** (paste your API key, then add/seed data
visually). CSV bulk upload supported.

| Method | Path | Purpose |
|---|---|---|
| `POST`/`GET` | `/buyers` · `/buyers/{id}` | Create / list / read / edit (`PATCH`) buyers |
| `GET`  | `/buyers/{id}/payment-summary` | Derived signals: on-time rate, avg delay, bounces, overdue, outstanding |
| `POST`/`GET` | `/buyers/{id}/orders` (+ `/bulk`) | Add / list a buyer's orders |
| `POST` | `/orders/{id}/pay` · `/orders/{id}/bounce` | Mark paid (with date) / flag a bounce |
| `PATCH`| `/orders/{id}` | Edit an order |
| `POST` | `/payment-history/import-csv` | Bulk upload buyers + orders |
| `POST` | `/payment-history/seed-sample` | Generate 3 sample buyers (good/slow/risky) |
| `GET`  | `/simulator` | Manual simulator UI (browser) |

### Phase 2 — GST data: cache & cost control
Every GST lookup goes through a shared cache (per `gstin`+provider, TTL `GST_CACHE_TTL_DAYS`,
default 30) so the same GSTIN isn't fetched (or paid for) twice. Every call — cache hit or
live — is logged with its cost and latency.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/gst/usage` | Aggregate: total/live calls, cache hits, hit rate, total cost |
| `GET` | `/gst/calls` | Recent GST lookup log (per call: hit, success, cost, latency) |

Per-call cost is declared on each provider (`mock`=0, `sandbox`/`perfios`=placeholder) — set
to your contracted price.

### Phase 3 — MCA + legal data
Each report now also collects four more signal groups (best-effort — missing data never breaks
a report): **company** (CIN, incorporation, age, status, capital), **directors** (count + roster),
**charges** (open/satisfied secured loans), and **legal** (insolvency / recovery cases). Whether
an entity has MCA company data is inferred from its PAN type in the GSTIN (companies / LLPs do,
proprietors don't). Same cache + cost-log pattern as GST (`MCA_CACHE_TTL_DAYS`, default 30).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/mca/usage` | Aggregate MCA call/hit/cost totals |
| `GET` | `/mca/calls` | Recent MCA + legal lookup log |

### Phase 4 — Feature dataset + rule-based score
Reports now carry a **rule-based credit score** (0–100), a **risk band** (Low / Medium / High),
and an explainable **breakdown** (each signal's weight, sub-score, and contribution). The score
is a weighted blend over whatever signals are present; missing groups drop out and weights
renormalise. Two hard overrides force High risk regardless of the blend: active insolvency and a
cancelled GST registration (plus company under liquidation / struck off).

The same signals are flattened into a clean, versioned **feature dataset** — one row per business
with all signals as features + the payment outcome as the label — ready for Part B (model training).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/credit-signal/features/build` | Build/rebuild a snapshot for a `{ "gstin": "..." }` (optional `buyer_id`, `as_of_date`) |
| `GET`  | `/credit-signal/features` | List your snapshots (optional `?gstin=`) |
| `GET`  | `/credit-signal/features/{id}` | Read one snapshot (full features + label + breakdown) |
| `GET`  | `/credit-signal/dataset` | Export the labelled dataset (`?format=json` or `csv`) — latest version per business |

## Setup

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and a local PostgreSQL 17.

```bash
# 1. Install deps into a local venv
uv sync

# 2. Configure
cp .env.example .env        # adjust DATABASE_URL / password if needed

# 3. Create the database + tables
uv run py scripts/init_db.py

# 4. Create a supplier + API key (prints the key once — save it)
uv run py scripts/seed.py "Acme Supplies"

# 5. Run the app (http://localhost:8120, docs at /docs)
uv run py -m app.main
```

## Test it

```bash
KEY=<the key printed by seed.py>

# Create a report (mock provider returns realistic fake GST data)
curl -X POST http://localhost:8120/credit-signal/reports \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"gstin":"27AAPFU0939F1ZV"}'

# Read it back by id
curl http://localhost:8120/credit-signal/reports/<id> -H "X-API-Key: $KEY"
```

A Bruno collection is in [bruno/](bruno/). Set the `apiKey` env var first.

### GSTIN validation

GSTINs are validated for structure **and** check digit. To feed made-up test GSTINs that
don't carry a valid checksum, set `VALIDATE_GSTIN_CHECKSUM=false` in `.env`.

### Switching to real GST data

The `GstProvider` interface is swappable via `GST_PROVIDER`:

- **`sandbox`** — [Sandbox.co.in](https://sandbox.co.in) (Quicko). Self-serve and free to start.
  Sign up to get an API key + secret, put them in `.env`, set `GST_PROVIDER=sandbox`, restart.
  Real identity (Search GSTIN) **and** compliance (Track GST Returns) for real GSTINs.
- **`perfios`** — Perfios/Karza. See [PERFIOS_SETUP.md](PERFIOS_SETUP.md). Enterprise signup;
  base URL / path / auth header / response mapping are `.env`-configurable.

Both are real implementations of the same interface, so swapping providers needs no app changes.
