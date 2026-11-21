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

**Let judges try it from their phones:** on a laptop with normal internet, run in a second terminal
`cloudflared tunnel --url http://localhost:8000` (or `ngrok http 8000`) and share the printed https URL.
Phone camera capture needs HTTPS, which the tunnel provides.

**Collect eval clips from a phone:** set `EVAL_UPLOAD_KEY` in `.env`, then open `/eval-upload?k=<key>`. Clips land in `eval/clips/` with `labels.json` (git-ignored).

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

## Evaluation (5 Sigma-style: messy inputs vs a simple baseline)

`eval/eval.py` runs two systems on every clip:

- **full**: Gemini 4 watches the whole clip, then specs and queries, Shop search by text and keyframe photo, the Decisions fit gate, and the Gemini 4 top 3.
- **baseline**: the middle still frame only. Gemini 4 writes one plain query, we run one Shop text search and take the first 3 results.

Metrics:

- **kw@k**: the top-k offers contain all expected keywords.
- **judge@k**: a strict Gemini 4 judge, which sees only the ground-truth label and the offers, says an offer would actually fix it.
- **Latency.**

Every miss is written to a failure log.

```bash
.venv/bin/python eval/eval.py                                  # your clips: eval/clips + eval/clips/labels.json
.venv/bin/python eval/eval.py --clips eval/samples             # synthetic smoke set (build with eval/samples/make_samples.sh)
```

Output goes to `eval/results/<timestamp>/` as `summary.md`, `failures.md` and `results.json`.

### Results so far: synthetic smoke set (8 clips = 4 items × clean/messy)

Each "messy" clip is a dark, low-contrast, blurred, noisy, shaky handheld pan made from public Wikimedia photos.
These are **not** real phone footage, and the real-clip numbers below replace them.

| System | kw@3 | judge@3 | median latency |
|---|---|---|---|
| **Fix-It Cam (full video)** | **8/8 (100%)** | **8/8 (100%)** | 19.2 s |
| Baseline (1 frame + plain search) | 6/8 (75%) | 3/8 (38%) | 3.3 s |

What the baseline gets wrong (from `eval/smoke_results/failures.md`):

- **Right words, wrong product.** For a frayed *MacBook* MagSafe cable, the baseline searched "Apple MagSafe charger" and returned three *iPhone wireless* MagSafe chargers. Keyword match says "hit", but the judge says no. Fix-It Cam read the cable's shape and clip across frames, asked for a MagSafe 1/2 *power adapter*, and its Decisions gate pushed wireless pads down.
- **One bad frame ruins it.** On the dark, shaky MacBook clip, the middle frame looked like a pen, and the baseline shopped for ballpoint pens. On the messy aerator clip it shopped for garden-hose couplers.
- **Missing specs.** For worn *metallic* disc brake pads, the baseline returned resin and organic pads.

### Real messy phone clips

_Pending: 20–30 clips filmed at the venue. Upload them at `/eval-upload?k=<EVAL_UPLOAD_KEY>` and run `eval/eval.py`._

**How to film the eval set (aim for 20–30 clips, 5–10 s each):**

- Use 8–12 different broken or worn items: chargers and cables, earbuds, faucet parts, zippers, straps, bulbs, batteries, wiper blades, bike parts, glasses screws, phone cases.
- Film each item 2–3 times, messier each time:
  1. normal light
  2. dim or backlit, with the label only visible for a moment
  3. shaky, part covered by a hand, background noise, and say the model number out loud instead of showing it
- In at least a few clips, put the deciding spec (wattage, connector, size) in only one moment or only in the audio. That is where watching the whole video should beat one frame.
- Label each upload with keywords the correct replacement must contain, e.g. `usb-c, 60w` or `aerator`.

## Where it breaks

- **No model number visible or spoken.** It falls back to a family ("MagSafe 1 or 2, 45–85 W") and says so in `uncertainties`. The ranking adds a "check before buying" note, but the user still has to confirm.
- **Catalog coverage.** Shop's catalog is strong on consumer goods and weaker on OEM appliance and automotive parts. The pipeline then returns the closest whole-item replacement or a generic part (e.g. a universal aerator).
- **Speed.** About 17–30 s end to end. Most of it is Gemini 4 video understanding (6–20 s, varies by call). Upload, search (~1 s) and the Decisions gate (~0.5 s) are cheap.
- **The keyframe is one frame.** Photo search uses the frame Gemini picks as clearest. If the part is never clearly in view, photo search adds noise, and the gate filters it.
- **Keyword metric is gameable.** Hence the strict LLM judge column. The MagSafe-wireless case is the clearest example.
- **Checkout.** A checkout link is created live per merchant. Shipping address, payment and any extra steps (`requires_escalation`) happen on the merchant's page.

## Limitations

- The smoke results use 8 synthetic clips. Real phone footage is the eval that counts.
- The fit gate and the judge are both Gemini models, so their failure modes may correlate. The judge sees the ground-truth label, which the gate never does.
- Search is US/USD by default (`search_catalog` context).
- No accounts and no order history. One item per checkout.

## 1-minute demo script

| Time | Shot | Voice-over |
|---|---|---|
| 0:00–0:08 | Hand holds a frayed charger or leaky aerator | "Something breaks. You don't know the part name, the wattage or the thread size. You just know it's broken." |
| 0:08–0:25 | Phone: **Film it**, a shaky 6 s clip, saying "it's from my 2015 MacBook" | "Fix-It Cam: film it. Gemini 4 watches *and listens* to the whole clip…" |
| 0:25–0:35 | Diagnosis card: part, spec chips (seen / heard / inferred), tap a timestamp to jump the video | "…finds the exact part and specs, and shows you where in the video it saw them." |
| 0:35–0:45 | Top-3 cards with fit %, reasons and "check before buying" | "Shop catalog search by words *and* by a keyframe photo. The Gemini Decisions API scores the fit of every offer in half a second, and Gemini 4 picks the top 3." |
| 0:45–0:52 | Tap **Buy now**, a real Shop checkout opens | "One tap to a real checkout. You pay on the merchant's page." |
| 0:52–1:00 | Eval table: full vs baseline, plus one failure example | "On messy clips, one frame plus a search got N% right. Watching the whole video got M%. Here's where it still breaks." |

