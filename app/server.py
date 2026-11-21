"""FastAPI server: single-page app + streaming analyze endpoint + live checkout creation."""
from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from . import gemini, pipeline  # noqa: E402
from .shop_mcp import ShopMCP, ShopMCPError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))

app = FastAPI(title="Fix-It Cam")


@app.get("/")
async def index():
    return FileResponse(ROOT / "static" / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/health")
async def health():
    return {"ok": True, "identify_model": gemini.IDENTIFY_MODEL, "rank_model": gemini.RANK_MODEL,
            "gate_model": gemini.DECISION_MODEL, "gemini_key": bool(os.getenv("GEMINI_API_KEY"))}


def _ev(kind: str, **data) -> bytes:
    return (json.dumps({"event": kind, **data}) + "\n").encode()


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), note: str = Form("")):
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    if not (mime.startswith("video/") or mime.startswith("image/")):
        raise HTTPException(400, f"Please upload a video or photo (got {mime}).")
    suffix = Path(file.filename or "clip").suffix or (".mp4" if mime.startswith("video/") else ".jpg")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    size = 0
    while chunk := await file.read(1 << 20):
        size += len(chunk)
        if size > MAX_UPLOAD_MB << 20:
            tmp.close(); os.unlink(tmp.name)
            raise HTTPException(413, f"File too large (max {MAX_UPLOAD_MB} MB)")
        tmp.write(chunk)
    tmp.close()
    path = tmp.name
    # Phones often send video/quicktime; Gemini accepts it, keep as-is.

    async def stream():
        shop = ShopMCP()
        t_all = time.time()
        timings: dict = {}
        try:
            yield _ev("stage", stage="upload", label="Sending footage to Gemini 4…")
            t = time.time()
            part = await pipeline.media_part(path, mime)
            timings["upload_s"] = round(time.time() - t, 2)
            yield _ev("stage", stage="diagnose", label=f"{gemini.IDENTIFY_MODEL} is watching the clip…")
            t = time.time()
            diag = await gemini.diagnose(part, note)
            timings["diagnose_s"] = round(time.time() - t, 2)
            yield _ev("diagnosis", diagnosis=diag, timings=timings)

            frame = None
            if pipeline.is_video(mime):
                fb = await asyncio.to_thread(pipeline.extract_frame, path, float(diag.get("best_frame_seconds") or 0))
                frame = (fb, "image/jpeg") if fb else None
            else:
                frame = (open(path, "rb").read(), mime)
            yield _ev("stage", stage="search", label="Searching Shop catalog by words and by keyframe photo…")
            t = time.time()
            cands = await pipeline.search_offers(shop, diag, frame)
            timings["search_s"] = round(time.time() - t, 2)
            yield _ev("stage", stage="gate", label=f"Gemini Decisions checking fit of {len(cands)} offers…")
            if cands:
                t = time.time()
                try:
                    fits = await gemini.fit_gate(diag, cands)
                    for c, f in zip(cands, fits):
                        c["fit"] = round(f, 3)
                    cands.sort(key=lambda c: -c.get("fit", 0))
                except Exception as e:
                    timings["gate_error"] = str(e)[:200]
                timings["gate_s"] = round(time.time() - t, 2)
            yield _ev("stage", stage="rank", label="Gemini 4 picking the top 3 for fit…")
            shortlist = [c for c in cands if c.get("fit", 1) >= 0.05][:8] or cands[:8]
            t = time.time()
            top = await gemini.rank(diag, shortlist) if shortlist else []
            timings["rank_s"] = round(time.time() - t, 2)
            timings["total_s"] = round(time.time() - t_all, 2)
            yield _ev("results", top=top, considered=len(cands), timings=timings)
        except Exception as e:
            yield _ev("error", message=str(e)[:400])
        finally:
            await shop.aclose()
            try:
                os.unlink(path)
            except OSError:
                pass

    return StreamingResponse(stream(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


class CheckoutReq(BaseModel):
    shop: str
    variant_id: str
    quantity: int = 1


@app.post("/api/checkout")
async def checkout(req: CheckoutReq):
    """Create a real Shop checkout for one merchant and return continue_url exactly as returned.
    The shopper reviews and pays on the merchant page; we never call complete_checkout."""
    shop = ShopMCP()
    try:
        r = await shop.create_checkout(req.shop, req.variant_id, max(1, min(req.quantity, 5)))
    except ShopMCPError as e:
        return JSONResponse({"error": str(e)[:300]}, status_code=502)
    finally:
        await shop.aclose()
    url = r.get("continue_url")
    if not url:
        return JSONResponse({"error": "No checkout link returned", "messages": r.get("messages")}, status_code=502)
    total = next((t.get("amount") for t in r.get("totals", []) if t.get("type") == "total"), None)
    return {"continue_url": url, "status": r.get("status"), "total_minor": total, "currency": r.get("currency")}


# ---------------------------------------------------------------------------
# Eval clip collection: bulk-upload messy phone clips with expected part keywords.
EVAL_DIR = ROOT / "eval" / "clips"
LABELS = EVAL_DIR / "labels.json"
EVAL_UPLOAD_KEY = os.getenv("EVAL_UPLOAD_KEY", "")


def _check_key(k: str):
    if EVAL_UPLOAD_KEY and k != EVAL_UPLOAD_KEY:
        raise HTTPException(403, "Bad or missing upload key (?k=...)")


def _load_labels() -> dict:
    try:
        return json.loads(LABELS.read_text())
    except Exception:
        return {}


@app.get("/eval-upload")
async def eval_upload_page(k: str = ""):
    _check_key(k)
    return FileResponse(ROOT / "static" / "eval_upload.html", headers={"Cache-Control": "no-store"})


@app.get("/api/eval-clips")
async def eval_clips(k: str = ""):
    _check_key(k)
    return _load_labels()


@app.post("/api/eval-upload")
async def eval_upload(files: list[UploadFile] = File(...), keywords: str = Form(...),
                      description: str = Form(""), k: str = Form("")):
    _check_key(k)
    kws = [w.strip() for w in keywords.replace(";", ",").split(",") if w.strip()]
    if not kws:
        raise HTTPException(400, "Give at least one expected keyword")
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    labels = _load_labels()
    saved = []
    for f in files:
        mime = f.content_type or mimetypes.guess_type(f.filename or "")[0] or ""
        if not (mime.startswith("video/") or mime.startswith("image/")):
            continue
        stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in Path(f.filename or "clip").stem)[:40]
        name = f"{time.strftime('%H%M%S')}_{len(labels):03d}_{stem}{Path(f.filename or '').suffix.lower() or '.mp4'}"
        with open(EVAL_DIR / name, "wb") as out:
            while chunk := await f.read(1 << 20):
                out.write(chunk)
        labels[name] = {"keywords": kws, "description": description, "mime": mime}
        saved.append(name)
    LABELS.write_text(json.dumps(labels, indent=2))
    return {"saved": saved, "total_clips": len(labels)}


def main():
    import uvicorn
    uvicorn.run("app.server:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
