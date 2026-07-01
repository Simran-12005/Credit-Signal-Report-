# GST Data Provider — Research & Recommendation

## What we actually need

For a Credit Signal Report we look up **someone else's GSTIN** (the buyer) and want their:
- Identity (legal name, registration date, type, state, status)
- **Filing/compliance history** (GSTR-1 / GSTR-3B filed on time, gaps, cancellation/suspension)

Key point: we are **not filing returns on our own behalf** — we are reading public + compliance data about a third-party GSTIN. This shapes the choice below.

---

## Option 1 — Direct integration with the Govt GST portal (GSTN)

You cannot call GSTN APIs directly as an app. Access is gated through the **GSP / ASP model**:
- **GSP (GST Suvidha Provider):** licensed entity with a secure tunnel to GSTN.
- **ASP (Application Service Provider):** builds apps on top, feeds data through a GSP.

**Becoming a GSP yourself is not realistic for an MVP:**
- Must be an India-registered IT / BFSI company.
- **Paid-up capital ₹2–5 crore** and **avg turnover ₹5–10 crore** over last 3 years (varies by batch).
- Sign a formal contract + SLA with GSTN, security audits, license key.

| Pros | Cons |
|---|---|
| Authoritative, first-party data | Huge eligibility bar (₹ crore capital + turnover) |
| No reseller markup per call | Long onboarding, contracts, audits |
| Full API surface | Mostly designed for *filing*, not third-party lookups |
| | Months of effort — kills the "launch in weeks" goal |

➡️ **Verdict:** Not for the MVP. Revisit only at large scale, and even then likely via a GSP partner, not a direct license.

---

## Option 2 — Third-party GST data / verification API providers (recommended)

These are GSPs or ASPs that resell clean REST APIs. They handle the GSTN tunnel; we just call an endpoint with a GSTIN. This is how almost every fintech/lender does it.

### Provider comparison

| Provider | Strength for us | Pros | Cons |
|---|---|---|---|
| **Karza (now Perfios)** | Deepest **credit/underwriting** GST stack — filing history, turnover estimation, compliance scoring | Built for lenders/NBFCs; rich derived signals, not just verification; strong data-intelligence reputation | Enterprise sales motion; pricing opaque; can be pricier |
| **Perfios** | Strong financial-data platform; 99.9% uptime SLA | Enterprise-grade reliability, large client base, now owns Karza's stack | Geared to bigger clients; pricing on request |
| **Clear (ClearTax)** | Is itself a **GSP**; deep GST domain | First-party GSP access, mature GST APIs, good docs | More compliance/filing-oriented than credit-signal-oriented |
| **Signzy** | Customisable onboarding/KYB flows | Good if we want orchestrated KYB journeys end-to-end | Heavier than a plug-and-play API; overkill for simple lookups |
| **Surepass** | Cheap, plug-and-play verification | Affordable, batch processing, 3000+ clients, fast integration | More "verify GSTIN" than deep filing-history/compliance depth |
| **Others** (HyperVerge, Cashfree, Attestr, IDfy, Gridlines, BeFiSc) | Commodity GSTIN verification | Easy, cheap, instant | Mostly identity verification; thin on filing-history depth |

### Two tiers of data (matters for our scoring)

1. **GSTIN verification** (identity, status) — every provider has this, cheap, commodity.
2. **Returns filing history / compliance / turnover signals** — fewer providers do this well. **Karza/Perfios and Clear** are the strongest here, and this is exactly what our credit signals need.

---

## Recommendation

**Go with Option 2. Pick one provider behind a swappable interface.**

- **Primary choice: Karza (Perfios)** — its GST stack was purpose-built for lending/underwriting and returns the filing-history + compliance + turnover signals our risk model needs, not just "is this GSTIN valid".
- **Strong alternative: Clear (ClearTax)** — a real GSP with mature GST APIs, good if we want a more compliance-native partner.
- **For a cheap quick start / pilot:** **Surepass** for basic verification, then upgrade to Karza/Perfios once we need filing-history depth.

**Build a `GstProvider` interface** with one concrete implementation first, so we can switch or add a provider without touching the rest of the system. Cache every response and log cost per call (these APIs are paid and rate-limited).

---

## Testing / Sandbox options (build without paying)

Two layers — use both:

### 1. First: a mock provider (zero cost, zero API calls)
Build a `MockGstProvider` implementation of the `GstProvider` interface that returns realistic
fake identity + filing/compliance data. This lets us develop and test the **entire** scoring and
report flow offline — no API keys, no rate limits, no payment. This is the Phase 0 stub.

### 2. Then: free sandbox / free-credit tiers for real GSTIN data

| Provider | Free testing | Fit for us |
|---|---|---|
| **Perfios** | **10,000+ free sandbox credits** | ⭐ Best — same family as Karza (our production pick), so we test the real credit signals for free |
| **Sandbox.co.in** (by Quicko) | Free to start; Search GSTIN + return-status APIs, good docs + test cases | Strong dev experience; return-status gives compliance data |
| **AppyFlow** | 50 free requests | Basic GSTIN verification only — too shallow for credit scoring |
| **GSTINCheck** | 20 free requests (email signup) | Quick smoke test only |
| **Govt GST Developer Portal** | Sandbox + sample data/test keys | Production is GSP-gated; sandbox fine for trials |
| Manual lookup | Govt "Search Taxpayer" page / Masters India search tool | No API — eyeball-verify a few GSTINs by hand |

**Approach:** develop against `MockGstProvider` first, then validate against the **Perfios sandbox
(10k free credits)** — since it's the same stack as Karza, nothing changes when we go to production.

---

## Sources
- [Top GST Verification API Providers in India (2026) — Surepass](https://surepass.io/blog/top-gst-verification-api-providers/)
- [Best KYC API Providers India 2026 — BeFiSc](https://www.befisc.com/fintechsherlock/best-kyc-api-providers-india-2026/)
- [GST Verification API — Perfios](https://perfios.ai/gst-verification-api/)
- [Karza GST Verification API pricing — TrustRadius](https://www.trustradius.com/products/karza-gst-verification-api/pricing)
- [All You Need to Know About GST API Access — ClearTax](https://cleartax.in/s/gst-api-access)
- [Role of GSP and ASP in GST India — Avalara](https://www.avalara.com/in/en/resources/whitepapers/role-gsp-asp-gst-india.html)
- [GSP ecosystem — GSTN](https://www.gstn.org.in/gsp-ecosystem)
- [GST Suvidha Provider eligibility — IndiaFilings](https://www.indiafilings.com/learn/gst-suvidha-provider-gsp)
- [GSP eligibility criteria batch 4 (PDF) — GSTN](https://www.gstn.org.in/assets/mainDashboard/Pdf/eligibility-batch-4.pdf)
- [Sandbox.co.in GST APIs](https://sandbox.co.in/gst) · [Search GSTIN docs](https://developer.sandbox.co.in/reference/search-gstin-api)
- [AppyFlow Verify GST (free quota)](https://appyflow.in/verify-gst/)
- [GSTINCheck — free API key](https://gstincheck.co.in/)
- [GST Developer Portal (sandbox)](https://developer.gst.gov.in/apiportal/)
