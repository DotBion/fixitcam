# Fix-It Cam 🔧

**Film the broken thing. Gemini 4 finds the exact part. Buy the replacement in one tap.**

Point your phone at something broken (a frayed charger, a leaky faucet aerator, a snapped strap) for 5–10 seconds.
Gemini 4 watches *and listens to* the clip, identifies the item, the broken part and the specs you need
(connector, size, wattage, thread…), cites the timestamps it used, and gives a repair tip. Fix-It Cam then searches the live
Shop catalog by **words and by a keyframe photo**, checks every offer's fit with the **Gemini Decisions API**, has Gemini 4 pick the top 3,
and **Buy now** opens a real Shop checkout.

> Built for the Gemini 4 NYC Hackathon. Theme: **Element 119** (video is the product), evaluated 5 Sigma-style against a single-frame baseline. Also targets the Shopify prize (real purchases through Shop MCP).

## How it works

```mermaid
flowchart LR
  A[Phone clip / photo] -->|Files API| B[Gemini 4 Hydrogen<br/>structured diagnosis JSON<br/>item · part · specs · evidence timestamps]
  B --> C[ffmpeg keyframe<br/>at best_frame_seconds]
  B -->|2-3 queries| D[Shop MCP search_catalog<br/>text]
  C -->|like: image| E[Shop MCP search_catalog<br/>photo + text]
  D & E --> F[Gemini Decisions API<br/>gemini-decision-1<br/>P(fits) per offer, one call]
  F --> G[Gemini 4 ranks top 3<br/>with reasons + what to check]
  G --> H[Buy now → create_checkout<br/>→ continue_url opened unchanged]
```

| Step | Model / tool | Typical latency |
|---|---|---|
| Diagnose video | `gemini-4-hydrogen` (Files API, JSON schema) | 5–10 s |
| Search | Shop MCP `search_catalog` (3 text queries + 1 image query, parallel) | ~1 s |
| Fit gate | Gemini Decisions API `gemini-decision-1` (one `noul` question per offer) | ~0.5 s |
| Rank | `gemini-4-hydrogen`, thinking `low` | 2–6 s |
| Checkout | Shop MCP `create_checkout` → `continue_url` | ~1 s |

Shop rules we follow: products are fetched live on every request (no caching), merchant images load from their original URLs,
product and checkout URLs are used exactly as returned, one merchant per checkout, and the shopper reviews and pays on the merchant's page.
The app never calls `complete_checkout`.

## Run it

```bash
cp .env.example .env      # put your GEMINI_API_KEY in .env
./run.sh                  # creates .venv, installs deps, serves http://localhost:8000
```

Requires Python 3.11+ and `ffmpeg` (for the keyframe photo search; without it the app still works with text search).

**Let judges try it from their phones:** in a second terminal run
`cloudflared tunnel --url http://localhost:8000` (or `ngrok http 8000`) and share the printed https URL.
Phone camera capture needs HTTPS, which the tunnel provides.

CLI smoke test (diagnosis → top 3 → real checkout link, no purchase):

```bash
.venv/bin/python scripts/smoke_test.py path/to/clip.mp4
```

Config (env): `IDENTIFY_MODEL` (default `gemini-4-hydrogen`), `RANK_MODEL`, `DECISION_MODEL` (`gemini-decision-1`),
`DIAGNOSE_THINKING`, `RANK_THINKING` (default `low`), `PORT`.

## Code map

- `app/gemini.py`: diagnosis schema and prompt, Decisions fit gate, ranking
- `app/shop_mcp.py`: plain HTTP JSON-RPC client for Shop MCP (protocol `2026-07-28`, stateless)
- `app/pipeline.py`: keyframe extraction, multi-query search with merge and dedupe, end-to-end `run()`
- `app/server.py`: FastAPI with `/api/analyze` (streams NDJSON progress events), `/api/checkout`, `/api/health`
- `static/index.html`: mobile-first single-page app (film, upload, diagnosis with tap-to-seek evidence timestamps, product cards, Buy)

## Evaluation

_Coming next: `eval/eval.py` compares the full video pipeline with a single-still-frame + plain-text-search baseline on messy clips (top-3 hit rate, failure log)._
