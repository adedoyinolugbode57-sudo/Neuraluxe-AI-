# main.py
"""
Neuraluxe-AI v10k Hyperluxe — Large Single-file Server
Author: ChatGPT + Joshua Dav
Purpose:
 - Consolidates the major features of the Neuraluxe-AI ecosystem into one
   comprehensive and copy-paste-ready Flask application.
 - Includes optional OpenAI connectivity, marketplace simulation, voice + TTS
   placeholders, payments mock, analytics, admin operations, scheduler, and
   an environment verification route for Render deployments.
 - Designed for Render (use gunicorn main:app as start command).
Notes:
 - Keep your secrets in Render environment variables (do NOT commit .env).
 - This file is intentionally verbose and commented for readability and
   future expansion.
"""

# -----------------------
# Standard library
# -----------------------
import os
import sys
import time
import json
import uuid
import math
import queue
import random
import logging
import threading
import sqlite3
import atexit
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from typing import Any, Dict, List, Optional

# -----------------------
# Third-party imports (soft)
# -----------------------
# We import Flask and Flask-Cors and fall back with helpful errors if missing.
try:
    from flask import Flask, request, jsonify, send_from_directory, abort, g
    from flask_cors import CORS
except Exception as e:
    raise RuntimeError("Flask and Flask-Cors are required. Install with: pip install Flask Flask-Cors") from e

# Optional packages — imported if present (we handle absent gracefully)
try:
    import openai
    OPENAI_INSTALLED = True
except Exception:
    OPENAI_INSTALLED = False

try:
    import requests
    REQUESTS_INSTALLED = True
except Exception:
    REQUESTS_INSTALLED = False

# Rich logging optionally available for CLI diagnostics
try:
    from rich.console import Console
    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False

# -----------------------
# App constants and env
# -----------------------
APP_NAME = os.getenv("APP_NAME", "Neuraluxe-AI")
VERSION = os.getenv("APP_VERSION", "v10k.Hyperluxe")
CREATORS = os.getenv("CREATORS", "ChatGPT + Joshua Dav")
PORT = int(os.getenv("PORT", 10000))
DEBUG = os.getenv("FLASK_ENV", "production").lower() != "production"
NEURA_ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "neura-admin-2025")
NEURA_DEV_FREE_EMAIL = os.getenv("NEURA_DEV_FREE_EMAIL", "adedoyinolugbode57@gmail.com")
OPENAI_ENABLED = os.getenv("OPENAI_ENABLED", "false").lower() in ("1", "true", "yes")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
ITEMS_SIMULATED_CAP = int(os.getenv("ITEMS_SIMULATED_CAP", 1000000))
ITEMS_PAGE_SIZE_DEFAULT = int(os.getenv("ITEMS_PAGE_SIZE_DEFAULT", 24))
SAFE_MAX_PAGE_SIZE = int(os.getenv("SAFE_MAX_PAGE_SIZE", 1000))
CACHE_WARM_PAGES = int(os.getenv("CACHE_WARM_PAGES", 5))
RATE_LIMIT_SECONDS = float(os.getenv("NEURA_RATE_LIMIT_SECONDS", 0.0))
DB_FILE = os.getenv("NEURA_DB", "neuraluxe.db")

# Configure OpenAI if possible
if OPENAI_ENABLED and OPENAI_API_KEY and OPENAI_INSTALLED:
    try:
        openai.api_key = OPENAI_API_KEY
    except Exception:
        pass

# -----------------------
# Logging
# -----------------------
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("neuraluxe")

if RICH_AVAILABLE:
    console = Console()
else:
    console = None

logger.info(f"Starting {APP_NAME} {VERSION} (DEBUG={DEBUG})")

# -----------------------
# Flask app
# -----------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# -----------------------
# Database (SQLite for simplicity)
# -----------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        need_init = not os.path.exists(DB_FILE)
        db = sqlite3.connect(DB_FILE, check_same_thread=False)
        db.row_factory = sqlite3.Row
        g._database = db
        if need_init:
            init_db(db)
    return db

def init_db(db_conn):
    logger.info("Initializing SQLite schema...")
    cur = db_conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        is_free INTEGER DEFAULT 0,
        transactions INTEGER DEFAULT 0,
        locked_until INTEGER DEFAULT 0,
        created_at INTEGER DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        item_id TEXT,
        amount REAL,
        currency TEXT,
        meta TEXT,
        created_at INTEGER
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        message TEXT,
        rating INTEGER,
        created_at INTEGER
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT,
        value TEXT,
        created_at INTEGER
    );
    """)
    db_conn.commit()
    # Seed developer free user
    ensure_user(NEURA_DEV_FREE_EMAIL, is_free=True)

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db:
        db.close()

def ensure_user(email: str, is_free: bool=False) -> Dict[str, Any]:
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    row = cur.fetchone()
    if row:
        return dict(row)
    now = int(time.time())
    cur.execute("INSERT INTO users (email,is_free,created_at) VALUES (?,?,?)", (email, 1 if is_free else 0, now))
    db.commit()
    return {"email": email, "is_free": is_free, "created_at": now}

# -----------------------
# Utilities
# -----------------------
def utc_ts() -> int:
    return int(time.time())

def make_id(prefix: str="id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def safe_float(s, default=None):
    try:
        return float(s)
    except Exception:
        return default

def pretty(obj):
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)

# -----------------------
# Basic security & auth decorators
# -----------------------
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization") or request.args.get("admin_token")
        if token and token.startswith("Bearer "):
            token = token.split(" ", 1)[1]
        if not token or token != NEURA_ADMIN_TOKEN:
            return jsonify({"error":"admin_required"}), 401
        return func(*args, **kwargs)
    return wrapper

# Rate limiter decorator
_rate_store = {}
def rate_limit(seconds: float):
    def decorator(f):
        @wraps(f)
        def inner(*args, **kwargs):
            if seconds <= 0:
                return f(*args, **kwargs)
            client = request.headers.get("X-Forwarded-For", request.remote_addr or "anon")
            now = time.time()
            last = _rate_store.get(client, 0)
            if now - last < seconds:
                retry = seconds - (now - last)
                return jsonify({"error":"rate_limited","retry_after": retry}), 429
            _rate_store[client] = now
            return f(*args, **kwargs)
        return inner
    return decorator

# -----------------------
# Simple in-memory caches for marketplace pages
# -----------------------
_items_cache_lock = threading.Lock()
_items_page_cache: Dict[str, Dict] = {}

def _page_key(page, size, q, category, min_p, max_p):
    return f"p{page}_s{size}_q{q or ''}_c{category or ''}_min{min_p or ''}_max{max_p or ''}"

# Deterministic pseudo-random generator
def mulberry32(seed: int) -> float:
    seed = int(seed) & 0xffffffff
    seed = (seed + 0x6D2B79F5) & 0xffffffff
    seed = (seed ^ (seed >> 16)) * 0x45d9f3b & 0xffffffff
    seed = (seed ^ (seed >> 16)) * 0x45d9f3b & 0xffffffff
    seed = seed ^ (seed >> 16)
    return (seed & 0xffffffff) / 4294967296.0

CATEGORIES = [
    "AI Tools","Automation","Trading","Freelancers","Design","Crypto","Voice","Education","Dev Plugins","AddOns"
]

def gen_item(i: int) -> Dict[str, Any]:
    i = max(1, int(i))
    r = mulberry32(i)
    category = CATEGORIES[i % len(CATEGORIES)]
    base = {
        "AI Tools":"Neuraluxe AI Toolkit",
        "Automation":"AutoFlow Bot",
        "Trading":"Neura Trader Pro",
        "Freelancers":"Freelance Booster",
        "Design":"Hyper Studio Pack",
        "Crypto":"Crypto Insight Module",
        "Voice":"Voice Pack",
        "Education":"Learning Pack",
        "Dev Plugins":"Dev Toolkit",
        "AddOns":"Legacy Addon"
    }.get(category, "Neuraluxe Asset")
    price = round(29.99 + (i % 1000) * ((9999.99 - 29.99)/1000) + (r * 50), 2)
    rating = round(3.0 + r * 2.0, 1)
    return {
        "id": f"nli-{i}",
        "name": f"{base} #{i}",
        "category": category,
        "price": price,
        "currency": "USD",
        "rating": rating,
        "description": f"A premium {category} asset curated by Neuraluxe — preview {i}.",
        "image": f"https://picsum.photos/seed/neuraluxe{i}/400/300",
        "created_at": utc_ts()
    }

def get_items_page(page:int=1, page_size:int=ITEMS_PAGE_SIZE_DEFAULT, q:Optional[str]=None, category:Optional[str]=None, min_price:Optional[float]=None, max_price:Optional[float]=None):
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), SAFE_MAX_PAGE_SIZE))
    key = _page_key(page, page_size, q, category, min_price, max_price)
    with _items_cache_lock:
        if key in _items_page_cache:
            return _items_page_cache[key]
    start = (page - 1) * page_size + 1
    items = []
    idx = start
    while len(items) < page_size and idx <= ITEMS_SIMULATED_CAP:
        it = gen_item(idx)
        if category and it["category"].lower() != category.lower():
            idx += 1; continue
        if q and q.lower() not in (it["name"] + " " + it["description"]).lower():
            idx += 1; continue
        if min_price is not None and it["price"] < float(min_price):
            idx += 1; continue
        if max_price is not None and it["price"] > float(max_price):
            idx += 1; continue
        items.append(it)
        idx += 1
    payload = {"page": page, "page_size": page_size, "items": items, "total_estimate": ITEMS_SIMULATED_CAP}
    with _items_cache_lock:
        _items_page_cache[key] = payload
    return payload

# Cache-warming thread
def warm_cache():
    logger.info("Warm cache starting...")
    for p in range(1, CACHE_WARM_PAGES + 1):
        try:
            get_items_page(page=p, page_size=ITEMS_PAGE_SIZE_DEFAULT)
            logger.debug(f"Warmed page {p}")
        except Exception:
            logger.exception("Warm cache error")
    logger.info("Warm cache finished")

threading.Thread(target=warm_cache, daemon=True).start()

# -----------------------
# Analytics persistence
# -----------------------
def record_analytics(key: str, value: Any):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO analytics (key, value, created_at) VALUES (?,?,?)", (key, json.dumps(value), utc_ts()))
        db.commit()
    except Exception:
        logger.exception("Failed to record analytics")

# -----------------------
# Payments mock (Opay/Payoneer placeholder)
# -----------------------
MAX_RETRIES = 3
LOCK_DURATION = 24 * 60 * 60  # 24 hours

def verify_payment_opay_mock(user_email: str, amount: float) -> Dict[str, Any]:
    # Developer bypass = free
    if user_email and user_email.lower() == NEURA_DEV_FREE_EMAIL.lower():
        return {"ok": True, "reason": "dev_free_bypass", "tx": make_id("tx")}
    try:
        amt = float(amount)
    except Exception:
        return {"ok": False, "reason": "invalid_amount"}
    if amt <= 100000:  # mock acceptance
        return {"ok": True, "reason": "mock_confirmed", "tx": make_id("tx")}
    return {"ok": False, "reason": "amount_too_large"}

def register_purchase(user_email: str, item_id: str, amount: float, currency: str="USD", meta: Optional[Dict]=None) -> int:
    db = get_db()
    cur = db.cursor()
    now = utc_ts()
    cur.execute("INSERT INTO purchases (user_email,item_id,amount,currency,meta,created_at) VALUES (?,?,?,?,?,?)",
                (user_email, item_id, float(amount), currency, json.dumps(meta or {}), now))
    db.commit()
    return cur.lastrowid

# -----------------------
# Chat / AI endpoints
# -----------------------
def call_openai_completion(prompt: str, model: str="gpt-4o-mini", max_tokens:int=256, temperature:float=0.7) -> str:
    if not (OPENAI_ENABLED and OPENAI_INSTALLED and OPENAI_API_KEY):
        raise RuntimeError("OpenAI not configured")
    # We attempt to call OpenAI in a robust way
    try:
        # If the openai client supports ChatCompletion
        if hasattr(openai, "ChatCompletion"):
            resp = openai.ChatCompletion.create(model=model, messages=[{"role":"user","content":prompt}], max_tokens=max_tokens, temperature=temperature)
            # multiple possible structures depending on openai-client version
            if isinstance(resp, dict) and "choices" in resp:
                try:
                    return resp["choices"][0]["message"]["content"]
                except Exception:
                    return str(resp)
            return str(resp)
        else:
            resp = openai.Completion.create(engine=model, prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            return resp.choices[0].text
    except Exception as e:
        logger.exception("OpenAI call failed")
        raise

def mock_ai_reply(prompt: str) -> str:
    r = mulberry32(abs(hash(prompt)) % 4294967296)
    canned = [
        "Sure — I can handle that for you.",
        "Interesting — here's a practical plan.",
        "Let's break this down into clear steps.",
        "I recommend starting with the high-impact task.",
        "Consider iterating on the idea using small experiments."
    ]
    return f"{canned[int(r * len(canned))]} (mock reply for: {prompt[:80]})"

@app.route("/api/chat", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_chat():
    payload = request.get_json() or {}
    prompt = payload.get("prompt") or payload.get("message") or ""
    user = payload.get("user_email") or "guest@example.com"
    model = payload.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not prompt:
        return jsonify({"error":"empty_prompt"}), 400
    record_analytics("chat_request", {"user": user, "len": len(prompt)})
    if OPENAI_ENABLED and OPENAI_INSTALLED and OPENAI_API_KEY:
        try:
            resp = call_openai_completion(prompt, model=model)
            return jsonify({"ok": True, "provider": "openai", "response": resp})
        except Exception:
            logger.warning("OpenAI failed: falling back to mock")
    resp = mock_ai_reply(prompt)
    return jsonify({"ok": True, "provider": "mock", "response": resp})

# -----------------------
# Healthcare endpoints (basic)
# -----------------------
@app.route("/api/health/symptoms", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_health_symptoms():
    payload = request.get_json() or {}
    symptoms = payload.get("symptoms","").strip()
    if not symptoms:
        return jsonify({"error":"missing_symptoms"}), 400
    advice = []
    s = symptoms.lower()
    if "fever" in s or "temperature" in s:
        advice.append("Monitor temperature, stay hydrated. Seek medical attention for >38.5°C.")
    if any(k in s for k in ["cough","sore throat","sneezing"]):
        advice.append("Rest, fluids, and consider a medical check if persistent.")
    if not advice:
        advice.append("Monitor symptoms and consult a healthcare professional if concerned.")
    record_analytics("health_symptom_check", {"symptoms": symptoms})
    return jsonify({"ok": True, "symptoms": symptoms, "advice": advice})

@app.route("/api/health/medication", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_health_medication():
    payload = request.get_json() or {}
    drug = (payload.get("drug") or "").strip()
    if not drug:
        return jsonify({"error":"missing_drug"}), 400
    mock = {
        "name": drug.title(),
        "brand_name": f"{drug.title()}-Brand",
        "manufacturer": "Neuraluxe Pharmaceuticals (demo)",
        "purpose": "General demonstration only",
        "dosage": "Consult official sources",
        "source": "mock"
    }
    record_analytics("med_lookup", {"drug": drug})
    return jsonify({"ok": True, "results": [mock]})

# -----------------------
# Marketplace endpoints
# -----------------------
@app.route("/api/market/items", methods=["GET"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_market_items():
    try:
        page = int(request.args.get("page", 1))
    except Exception:
        page = 1
    try:
        page_size = int(request.args.get("page_size", ITEMS_PAGE_SIZE_DEFAULT))
    except Exception:
        page_size = ITEMS_PAGE_SIZE_DEFAULT
    q = request.args.get("q")
    category = request.args.get("category")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    min_p = safe_float(min_price, None) if min_price else None
    max_p = safe_float(max_price, None) if max_price else None
    data = get_items_page(page=page, page_size=page_size, q=q, category=category, min_price=min_p, max_price=max_p)
    record_analytics("market_query", {"page": page, "q": q or "", "category": category or ""})
    return jsonify(data)

@app.route("/api/market/purchase", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_market_purchase():
    payload = request.get_json() or {}
    user_email = payload.get("user_email") or payload.get("email") or "guest@example.com"
    item_id = payload.get("item_id")
    amount = safe_float(payload.get("amount", 0.0), 0.0)
    if not item_id:
        return jsonify({"error":"missing_item_id"}), 400
    verify = verify_payment_opay_mock(user_email, amount)
    if verify.get("ok"):
        puid = register_purchase(user_email, item_id, amount)
        record_analytics("purchase", {"user": user_email, "item_id": item_id, "amount": amount})
        return jsonify({"ok": True, "purchase_id": puid, "tx": verify.get("tx")})
    return jsonify({"ok": False, "reason": verify.get("reason")}), 402

# -----------------------
# Feedback endpoint
# -----------------------
@app.route("/api/feedback", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_feedback():
    payload = request.get_json() or {}
    user = payload.get("user_email", "anonymous")
    message = payload.get("message", "")
    rating = int(payload.get("rating", 0))
    if not message:
        return jsonify({"error":"missing_message"}), 400
    db = get_db()
    cur = db.cursor()
    now = utc_ts()
    cur.execute("INSERT INTO feedbacks (user_email,message,rating,created_at) VALUES (?,?,?,?)", (user, message, rating, now))
    db.commit()
    record_analytics("feedback", {"user": user, "rating": rating})
    return jsonify({"ok": True, "id": cur.lastrowid})

# -----------------------
# Admin endpoints
# -----------------------
@app.route("/api/admin/analytics", methods=["GET"])
@admin_required
def api_admin_analytics():
    key = request.args.get("key")
    limit = int(request.args.get("limit", 100))
    db = get_db()
    cur = db.cursor()
    if key:
        cur.execute("SELECT * FROM analytics WHERE key=? ORDER BY created_at DESC LIMIT ?", (key, limit))
    else:
        cur.execute("SELECT * FROM analytics ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    return jsonify({"ok": True, "items": [dict(r) for r in rows]})

@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def api_admin_stats():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM users")
    users = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM purchases")
    purchases = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM feedbacks")
    feedbacks = cur.fetchone()["c"]
    uptime = int(time.time() - app_start_time)
    return jsonify({"ok": True, "users": users, "purchases": purchases, "feedbacks": feedbacks, "uptime_seconds": uptime})

@app.route("/api/admin/seed", methods=["POST"])
@admin_required
def api_admin_seed():
    db = get_db()
    cur = db.cursor()
    now = utc_ts()
    # seed users
    sample = [f"seed{i}@example.com" for i in range(1, 51)]
    for email in sample:
        try:
            cur.execute("INSERT INTO users (email,is_free,created_at) VALUES (?,?,?)", (email, 0, now))
        except Exception:
            pass
    # seed purchases
    for i in range(1, 101):
        cur.execute("INSERT INTO purchases (user_email,item_id,amount,currency,meta,created_at) VALUES (?,?,?,?,?,?)",
                    (sample[i % len(sample)], f"nli-{i}", float(29.99 + i), "USD", json.dumps({"seed": True}), now))
    db.commit()
    return jsonify({"ok": True, "seeded_users": len(sample), "seeded_purchases": 100})

# -----------------------
# Voice & TTS placeholders
# -----------------------
def synthesize_tts(text: str, engine: str="gtts", voice: str="default"):
    """
    Placeholder TTS integration.
    If you have pyttsx3 / gTTS / edge-tts available, you can replace this
    function with code that returns a URL or file path to the generated audio.
    """
    # Return mock URL and meta
    return {"ok": True, "url": f"https://storage.neuraluxe.ai/tts/{make_id('tts')}.mp3", "engine": engine, "voice": voice}

@app.route("/api/voice/tts", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_tts():
    payload = request.get_json() or {}
    text = payload.get("text","").strip()
    voice = payload.get("voice","default")
    engine = payload.get("engine", os.getenv("VOICE_ENGINE", "gtts"))
    if not text:
        return jsonify({"error":"missing_text"}), 400
    res = synthesize_tts(text, engine=engine, voice=voice)
    record_analytics("tts", {"len": len(text), "engine": engine})
    return jsonify(res)

@app.route("/api/voice/stt", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_stt():
    payload = request.get_json() or {}
    audio = payload.get("audio_base64")
    if not audio:
        return jsonify({"error":"missing_audio"}), 400
    # Return mock transcription
    transcription = "[transcription placeholder]"
    record_analytics("stt", {"size": len(audio)})
    return jsonify({"ok": True, "transcription": transcription})

# -----------------------
# Translation placeholder
# -----------------------
@app.route("/api/translate", methods=["POST"])
@rate_limit(RATE_LIMIT_SECONDS)
def api_translate():
    payload = request.get_json() or {}
    text = payload.get("text","").strip()
    target = payload.get("target","en")
    if not text:
        return jsonify({"error":"missing_text"}), 400
    # In a real implementation, use an external translate API
    translated = f"[{target}] {text}"
    record_analytics("translate", {"len": len(text), "target": target})
    return jsonify({"ok": True, "translated": translated})

# -----------------------
# /env/check and /ai/diagnose
# -----------------------
@app.route("/env/check", methods=["GET"])
def env_check():
    keys_to_check = [
        "APP_NAME","APP_VERSION","FLASK_ENV","PORT",
        "DATABASE_URL","VOICE_ENGINE","CACHE_TYPE",
        "OPENAI_ENABLED","OPENAI_MODEL"
    ]
    summary = {}
    for k in keys_to_check:
        v = os.getenv(k)
        if v and "KEY" not in k:
            summary[k] = v
        elif v:
            summary[k] = "✅ Loaded"
        else:
            summary[k] = "⚠️ Missing"
    return jsonify({
        "status": "success",
        "app": os.getenv("APP_NAME", APP_NAME),
        "version": os.getenv("APP_VERSION", VERSION),
        "env_summary": summary,
        "note": "If OPENAI_ENABLED=true and OPENAI_API_KEY present, cloud AI will be active."
    }), 200

@app.route("/ai/diagnose", methods=["GET"])
def ai_diagnose():
    openai_on = os.getenv("OPENAI_ENABLED", "false").lower() in ("1","true","yes")
    openai_key = os.getenv("OPENAI_API_KEY")
    result = {
        "ai_mode": "cloud" if openai_on and openai_key else "offline",
        "openai_key_present": bool(openai_key),
        "database_exists": os.path.exists(DB_FILE),
        "cache_warm_pages": CACHE_WARM_PAGES,
        "message": "diagnostic complete"
    }
    if openai_on and openai_key and OPENAI_INSTALLED:
        try:
            # lightweight check
            if hasattr(openai, "models"):
                _ = openai.models.list()
            result["openai_status"] = "connected"
        except Exception as e:
            result["openai_status"] = f"error: {e}"
    else:
        result["openai_status"] = "not-configured-or-not-installed"
    return jsonify(result)

# -----------------------
# Static file loader helper
# -----------------------
@app.route("/site/<path:path>", methods=["GET"])
def site_static(path):
    roots = ["static", "templates", "."]
    for r in roots:
        fp = os.path.join(r, path)
        if os.path.exists(fp):
            return send_from_directory(r, path)
    abort(404)

# -----------------------
# Background worker queue & scheduler
# -----------------------
job_queue = queue.Queue()

def job_worker():
    while True:
        job = job_queue.get()
        if job is None:
            break
        try:
            fn = job.get("fn")
            args = job.get("args", [])
            kwargs = job.get("kwargs", {})
            logger.info(f"Job start: {job.get('name')}")
            fn(*args, **kwargs)
            logger.info(f"Job done: {job.get('name')}")
        except Exception:
            logger.exception("Job error")
        finally:
            job_queue.task_done()

threading.Thread(target=job_worker, daemon=True).start()

def schedule_job(fn, name="job", delay=0, args=None, kwargs=None):
    if args is None: args=[]
    if kwargs is None: kwargs={}
    def runner():
        if delay > 0:
            time.sleep(delay)
        job_queue.put({"fn": fn, "args": args, "kwargs": kwargs, "name": name})
    threading.Thread(target=runner, daemon=True).start()
    return True

def nightly_maintenance():
    logger.info("Running nightly maintenance tasks")
    with _items_cache_lock:
        _items_page_cache.clear()
    try:
        db = get_db()
        cur = db.cursor()
        cutoff = utc_ts() - (90 * 24 * 3600)  # 90 days
        cur.execute("DELETE FROM analytics WHERE created_at < ?", (cutoff,))
        db.commit()
    except Exception:
        logger.exception("Nightly maintenance failed")
    logger.info("Nightly maintenance finished")

def _scheduler_loop():
    while True:
        try:
            now = datetime.utcnow()
            next_run = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            seconds = (next_run - now).total_seconds()
            logger.debug(f"Scheduler sleeping {seconds}s until next run")
            time.sleep(max(60, seconds))
            nightly_maintenance()
        except Exception:
            logger.exception("Scheduler loop exception")
            time.sleep(60)

threading.Thread(target=_scheduler_loop, daemon=True).start()

# -----------------------
# Startup & shutdown
# -----------------------
app_start_time = time.time()

def graceful_shutdown():
    logger.info("Graceful shutdown initiated")
    try:
        job_queue.put(None)
    except Exception:
        pass
    try:
        with _items_cache_lock:
            _items_page_cache.clear()
    except Exception:
        pass

atexit.register(graceful_shutdown)

# -----------------------
# Root & info
# -----------------------
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "app": APP_NAME,
        "version": VERSION,
        "creators": CREATORS,
        "uptime_seconds": int(time.time()-app_start_time),
        "status": "live"
    })

@app.route("/api/info", methods=["GET"])
def api_info():
    return jsonify({
        "app": APP_NAME,
        "version": VERSION,
        "creators": CREATORS,
        "developer_email": NEURA_DEV_FREE_EMAIL
    })

# -----------------------
# CLI helper: seed demo data (callable from runtime)
# -----------------------
def seed_demo_data(n_users=50, n_purchases=100):
    logger.info("Seeding demo data")
    db = get_db()
    cur = db.cursor()
    now = utc_ts()
    users = [f"demo{i}@example.com" for i in range(1, n_users+1)]
    for u in users:
        try:
            cur.execute("INSERT INTO users (email,is_free,created_at) VALUES (?,?,?)", (u, 0, now))
        except Exception:
            pass
    for i in range(1, n_purchases+1):
        u = users[i % len(users)]
        cur.execute("INSERT INTO purchases (user_email,item_id,amount,currency,meta,created_at) VALUES (?,?,?,?,?,?)",
                    (u, f"nli-{i}", float(29.99 + i), "USD", json.dumps({"seed": True}), now))
    db.commit()
    logger.info("Seeding complete")

# -----------------------
# Extra utilities for admin UI and exports
# -----------------------
@app.route("/api/admin/export_purchases", methods=["GET"])
@admin_required
def api_admin_export_purchases():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM purchases ORDER BY created_at DESC LIMIT 1000")
    rows = cur.fetchall()
    out = [dict(r) for r in rows]
    return jsonify({"ok": True, "count": len(out), "purchases": out})

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id,email,is_free,created_at FROM users ORDER BY created_at DESC LIMIT 500")
    rows = cur.fetchall()
    return jsonify({"ok": True, "users": [dict(r) for r in rows]})

# -----------------------
# Health & diagnostics endpoints
# -----------------------
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok", "time": utc_ts()})


# -----------------------
# 🛡️ Safety Notice Endpoint (for users to view)
# -----------------------
@app.route("/safety", methods=["GET"])
def safety():
    return jsonify({
        "message": (
            "Neuraluxe-AI is a demonstration platform. "
            "Medical, legal, and financial advice are provided for educational use only."
        )
    })

# -----------------------
# Final run
# -----------------------
if __name__ == "__main__":
    # Ensure DB initialized
    get_db()
    
    # Optionally seed demo content if env var is present
    if os.getenv("NEURA_SEED_DEMO", "false").lower() in ("1", "true", "yes"):
        seed_demo_data()
    
    # Log env summary to console (useful locally)
    logger.info(f"{APP_NAME} starting on 0.0.0.0:{PORT} (DEBUG={DEBUG})")
    
    # Run Flask dev server if executed directly (Render will use gunicorn)
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)