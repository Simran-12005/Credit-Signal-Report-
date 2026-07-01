# Wiring real Perfios GST data

The app works offline with the mock provider. To get **real** GST identity + compliance
data for real GSTINs, point it at the Perfios sandbox (10,000+ free credits, Karza stack).

## Step 1 — Get a sandbox key (you do this)

1. Go to **https://perfios.ai/gst-verification-api/** and request sandbox / API access
   (look for "Try in sandbox" / "Get API access" / "Contact us"). It's an enterprise
   signup, so you may need to fill a form and get a follow-up with credentials.
2. Once approved, log in to the **Perfios developer portal**. From there grab:
   - the **sandbox base URL** (e.g. `https://sandbox.perfios.ai` or a Karza host),
   - your **API key**,
   - the **GST search / verification** endpoint's docs (path + sample request + sample response).

> Faster free alternative if Perfios onboarding is slow: **Sandbox.co.in** (by Quicko) has
> self-serve, publicly documented Search-GSTIN + return-status APIs. We can wire that behind
> the same interface in minutes. Say the word.

## Step 2 — Send me 4 things (so I finish the wiring exactly)

From the sandbox docs, paste me:
1. **Base URL** + **endpoint path** for GSTIN search/verification.
2. **Auth**: the exact header name (e.g. `x-api-key`, `x-karza-key`, `Authorization: Bearer`).
3. A **sample request** (body params, e.g. whether `consent` is required).
4. A **sample response** JSON (so I map the real field names to our report).

A screenshot or copy-paste of the docs page is perfect.

## Step 3 — Configure (you, in .env)

For the common case you only edit `.env` — no code change:

```env
GST_PROVIDER=perfios
PERFIOS_BASE_URL=<sandbox base url>
PERFIOS_API_KEY=<your key>
PERFIOS_AUTH_HEADER=<x-api-key | x-karza-key | ...>
PERFIOS_GST_PATH=</gst/v1/search or whatever the docs say>
PERFIOS_CONSENT=Y
```

Then restart the app. `GET /health` will show `"gst_provider":"perfios"`, and creating a
report will fetch real data.

## Step 4 — Field mapping (I do this)

[app/services/gst/perfios_provider.py](app/services/gst/perfios_provider.py) `_map_response`
currently maps both Perfios-style and Karza-style field names as a best guess. Once you send
the real sample response, I align it exactly. That's the only code that should need touching.
