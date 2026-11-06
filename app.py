"""Paisa Ledger backend (Flask + SQLite). Run: python app.py"""
import hashlib
import json
import os
import re
import secrets
import threading
import time
from functools import wraps

from flask import Flask, g, jsonify, make_response, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

import db as database
from emi import build_schedule, summarise
from loan_csv import parse_loan_csv, to_number

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_SECONDS = 7 * 24 * 3600
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DUMMY_HASH = generate_password_hash("dummy-password-for-timing")  # equalises login timing for unknown emails


class ApiError(Exception):
    def __init__(self, status, message, **extra):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra


# ---- tiny in-memory login throttle: 10 failures / 15 min per IP+email ----
_attempts, _lock = {}, threading.Lock()


def _recent(key):
    now = time.time()
    _attempts[key] = [t for t in _attempts.get(key, []) if now - t < 900]
    return _attempts[key]


def too_many_attempts(key):
    with _lock:
        return len(_recent(key)) >= 10


def note_failure(key):
    with _lock:
        _recent(key).append(time.time())


def clear_failures(key):
    with _lock:
        _attempts.pop(key, None)


def create_app(db_file=None):
    app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "public"), static_url_path="")
    app.config["DB_FILE"] = db_file or os.environ.get("DB_FILE") or os.path.join(BASE_DIR, "data", "ledger.db")
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
    app.config["COOKIE_SECURE"] = os.environ.get("APP_ENV") == "production"
    if app.config["DB_FILE"] != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(app.config["DB_FILE"])), exist_ok=True)
    database.init_db(app.config["DB_FILE"])

    # ---------- per-request DB ----------
    def get_db():
        if "db" not in g:
            g.db = database.connect(app.config["DB_FILE"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    with app.app_context():
        get_db().execute("DELETE FROM sessions WHERE expires_at <= ?", (time.time(),))
        get_db().commit()

    # ---------- helpers ----------
    def body_json():
        if not (request.content_type or "").startswith("application/json"):
            raise ApiError(415, "Send JSON with Content-Type: application/json.")
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ApiError(400, "Invalid JSON.")
        return data

    def token_hash(t):
        return hashlib.sha256(t.encode()).hexdigest()

    def current_user():
        token = request.cookies.get("sid")
        if not token:
            return None
        return get_db().execute(
            "SELECT u.id, u.name, u.email FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?", (token_hash(token), time.time())).fetchone()

    def login_required(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            user = current_user()
            if not user:
                raise ApiError(401, "Please log in.")
            g.user = user
            return fn(*a, **kw)
        return wrapper

    def row_to_loan(r):
        return {"id": r["loan_id"], "borrower": r["borrower"], "principal": r["principal"],
                "rate": r["annual_rate"], "tenure": r["tenure_months"], "start": r["start_date"],
                "resets": {int(k): v for k, v in json.loads(r["resets"]).items()}}

    def get_loan(loan_id):
        r = get_db().execute("SELECT * FROM loans WHERE user_id = ? AND loan_id = ?",
                             (g.user["id"], loan_id)).fetchone()
        if not r:
            raise ApiError(404, "Loan not found.")
        return row_to_loan(r)

    def save_resets(loan):
        get_db().execute("UPDATE loans SET resets = ?, updated_at = datetime('now') WHERE user_id = ? AND loan_id = ?",
                         (json.dumps(loan["resets"]), g.user["id"], loan["id"]))
        get_db().commit()

    def schedule_response(loan):
        rows = build_schedule(loan)
        return jsonify({"loan": loan, "summary": summarise(loan, rows), "rows": rows})

    # ---------- auth routes ----------
    @app.post("/api/signup")
    def signup():
        b = body_json()
        name = str(b.get("name") or "").strip()
        email = str(b.get("email") or "").strip().lower()
        pw = str(b.get("pw") or "")
        if not name or len(name) > 100:
            raise ApiError(400, "Please enter your full name.")
        if not EMAIL_RE.match(email):
            raise ApiError(400, "Please enter a valid email address.")
        if len(pw) < 8:
            raise ApiError(400, "Use a password with at least 8 characters.")
        if len(pw) > 200:
            raise ApiError(400, "Password is too long.")
        conn = get_db()
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise ApiError(409, "This email already has an account. Log in instead.")
        conn.execute("INSERT INTO users (name, email, pw_hash) VALUES (?,?,?)",
                     (name, email, generate_password_hash(pw)))  # scrypt, salted
        conn.commit()
        return jsonify(ok=True), 201

    @app.post("/api/login")
    def login():
        b = body_json()
        email = str(b.get("email") or "").strip().lower()
        pw = str(b.get("pw") or "")
        key = f"{request.remote_addr}|{email}"
        if too_many_attempts(key):
            raise ApiError(429, "Too many attempts. Try again in a few minutes.")
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        ok = check_password_hash(u["pw_hash"] if u else DUMMY_HASH, pw) and u is not None
        if not ok:
            note_failure(key)
            raise ApiError(401, "Email or password is incorrect.")
        clear_failures(key)
        token = secrets.token_hex(32)
        conn.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?,?,?)",
                     (token_hash(token), u["id"], time.time() + SESSION_SECONDS))
        conn.commit()
        resp = make_response(jsonify(name=u["name"], email=u["email"]))
        resp.set_cookie("sid", token, max_age=SESSION_SECONDS, httponly=True, samesite="Lax",
                        secure=app.config["COOKIE_SECURE"], path="/")
        return resp

    @app.post("/api/logout")
    def logout():
        token = request.cookies.get("sid")
        if token:
            get_db().execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
            get_db().commit()
        resp = make_response(jsonify(ok=True))
        resp.set_cookie("sid", "", max_age=0, httponly=True, samesite="Lax", path="/")
        return resp

    @app.get("/api/me")
    def me():
        u = current_user()
        if not u:
            raise ApiError(401, "Not logged in.")
        return jsonify(name=u["name"], email=u["email"])

    # ---------- loan routes ----------
    @app.post("/api/loans/import")
    @login_required
    def import_loans():
        loans, errors = parse_loan_csv(body_json().get("csv"))
        if errors:
            return jsonify(error="The CSV has problems.", details=errors[:20], totalProblems=len(errors)), 422
        conn = get_db()
        try:
            conn.executemany(
                """INSERT INTO loans (user_id, loan_id, borrower, principal, annual_rate, tenure_months, start_date, resets)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(user_id, loan_id) DO UPDATE SET borrower=excluded.borrower,
                   principal=excluded.principal, annual_rate=excluded.annual_rate,
                   tenure_months=excluded.tenure_months, start_date=excluded.start_date,
                   resets=excluded.resets, updated_at=datetime('now')""",
                [(g.user["id"], l["id"], l["borrower"], l["principal"], l["rate"], l["tenure"],
                  l["start"], json.dumps(l["resets"])) for l in loans])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return jsonify(loans=loans)

    @app.get("/api/loans")
    @login_required
    def list_loans():
        rows = get_db().execute("SELECT * FROM loans WHERE user_id = ? ORDER BY loan_id", (g.user["id"],)).fetchall()
        return jsonify(loans=[row_to_loan(r) for r in rows])

    @app.get("/api/loans/<loan_id>/schedule")
    @login_required
    def loan_schedule(loan_id):
        return schedule_response(get_loan(loan_id))

    @app.post("/api/loans/<loan_id>/resets")
    @login_required
    def add_reset(loan_id):
        loan = get_loan(loan_id)
        b = body_json()
        month, rate = to_number(b.get("month")), to_number(b.get("rate"))
        if month is None or month != int(month) or not (2 <= month <= loan["tenure"]):
            raise ApiError(400, f"Enter a reset month between 2 and {loan['tenure']}.")
        if rate is None or not (0 <= rate <= 100):
            raise ApiError(400, "Enter a new annual rate between 0 and 100.")
        loan["resets"][int(month)] = rate
        save_resets(loan)
        return schedule_response(loan)

    @app.delete("/api/loans/<loan_id>/resets/<int:month>")
    @login_required
    def remove_reset(loan_id, month):
        loan = get_loan(loan_id)
        loan["resets"].pop(month, None)
        save_resets(loan)
        return schedule_response(loan)

    @app.delete("/api/loans/<loan_id>")
    @login_required
    def delete_loan(loan_id):
        get_loan(loan_id)
        get_db().execute("DELETE FROM loans WHERE user_id = ? AND loan_id = ?", (g.user["id"], loan_id))
        get_db().commit()
        return jsonify(ok=True)

    # ---------- errors, headers, frontend ----------
    @app.errorhandler(ApiError)
    def on_api_error(e):
        return jsonify(error=e.message, **e.extra), e.status

    @app.errorhandler(HTTPException)
    def on_http_error(e):
        msg = {413: "Request too large (max 2 MB).", 404: "Not found.", 405: "Method not allowed."}.get(e.code, e.description)
        if request.path.startswith("/api/"):
            return jsonify(error=msg), e.code
        return e

    @app.errorhandler(Exception)
    def on_error(e):
        app.logger.exception(e)
        return jsonify(error="Something went wrong on the server."), 500

    @app.after_request
    def headers(resp):
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    create_app().run(host="0.0.0.0" if os.environ.get("HOST_PUBLIC") else "127.0.0.1", port=port)
