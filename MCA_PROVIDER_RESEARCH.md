# MCA + Legal Data Provider — Research & Recommendation

Goal: replace the **mock** company / directors / charges / legal data (Phase 3) with real data,
the same way we did for GST. This note records what's available and the recommended path.

## What we need (per our normalized `McaData` shape)
- **company** — incorporation, age, status (active / strike-off / under liquidation), capital, RoC
- **directors** — count + roster (name, DIN, designation, dates)
- **charges** — secured loans registered against the company (open / satisfied, amounts)
- **legal** — insolvency (IBBI/NCLT) + recovery (NJDG/DRT/court) cases

## Headline finding
**Sandbox.co.in — the provider we already use for GST — also offers the MCA company data we need.**
Same account, same API key/secret, same auth flow, same base URL. So company/directors/charges
needs **no new signup** — just enabling/using the MCA product on the existing keys.

### Sandbox MCA Company Master Data API
- **Endpoint:** `POST {base}/mca/company/master-data/search`
  (`https://api.sandbox.co.in` live / `https://test-api.sandbox.co.in` test — same hosts as GST)
- **Auth:** identical to GST — `Authorization: <access_token>` (from `/authenticate`), `x-api-key`, `x-api-version`.
- **Body:** `{"@entity":"in.co.sandbox.kyc.mca.master_data.request","id":"<CIN or LLPIN>","consent":"Y","reason":"<20+ char purpose>"}`
- **Returns:** `data.company_master_data` (cin, company_name, date_of_incorporation, `company_status(for_efiling)`,
  roc_code, class_of_company, `paid_up_capital(rs)`, `authorised_capital(rs)`), `data.charges[]`
  (date_of_creation, charge_amount, status Active/Closed), `data["directors/signatory_details"][]`
  (name, din/pan, designation, begin_date, end_date).
- Covers **3 of our 4 groups**: company, directors, charges. ✅

## The one gap: GSTIN → CIN
The MCA API is keyed by **CIN** (company registration no.), but we start from a **GSTIN**. We can
extract the **PAN** from the GSTIN for free (chars 3–12), but still need PAN/name → **CIN**.
Sandbox's MCA product is CIN/DIN-only — **no PAN-to-CIN or company-search** endpoint confirmed.

Options to bridge it:
1. **Check the Sandbox dashboard** for a "company search" / "PAN to CIN" product on the same keys (cleanest if present).
2. **Add a small PAN→CIN lookup** from a provider that offers it: e.g. Attestr ("Company Search – name to CIN"),
   SurePass, or idspay (PAN-to-CIN). One cheap extra call, then feed the CIN to Sandbox MCA.
3. **Accept an optional CIN** on the report input for companies where the supplier already knows it.

Note: this whole path applies only to **companies / LLPs** (which have a CIN). **Proprietorships /
partnerships have no MCA data at all** — for them, GST + payment history is the whole picture, and
our scoring already handles "MCA not available" gracefully.

## Legal (insolvency / recovery cases) — separate provider
Sandbox does **not** cover court/insolvency data. Dedicated providers exist:
- **Attestr** — Court Record Check API (Supreme/High/District courts, tribunals).
- **SignalX** — Litigation Checks API (explicitly includes IBC/NCLT insolvency + recovery).
- **Vakeel360** — eCourts + all 15 NCLT benches (IBC cases), built for lenders/NBFCs.

Legal data is the **messiest and least standardized** (name-matching, false positives). Recommend
**deferring it** until company data is live; our scoring treats the legal group as optional.

## Recommended plan
1. **Phase A (now):** build a real `SandboxMcaProvider` for company/directors/charges, reusing the
   existing Sandbox keys. Solve GSTIN→CIN via option 1 (if Sandbox has it) or a small PAN→CIN call (option 2).
2. **Phase B (later):** add a legal provider (SignalX or Vakeel360) for insolvency/recovery, behind
   the same swappable interface.

Until Phase A ships, keep `MCA_PROVIDER=mock` so reports still produce a (clearly-labelled) score.

## Sources
- Sandbox MCA overview: https://developer.sandbox.co.in/api-reference/kyc/mca/overview
- Sandbox MCA company master data: https://developer.sandbox.co.in/reference/mca-company-master-data-api
- Sandbox new MCA contract: https://developer.sandbox.co.in/changelog/new-contract-for-mca-apis
- Attestr company search (name→CIN): https://docs.attestr.com/attestr-docs/company-search-api-name-to-cin
- idspay PAN→CIN: https://www.idspay.in/pan-to-cin
- SignalX litigation checks: https://signalx.ai/litigation-checks-api/
- Vakeel360 court/NCLT API: https://vakeel360.com/api
