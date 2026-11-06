# Paisa Ledger – Python backend (Flask + SQLite)

Backend for the Paisa Ledger frontend: accounts, per-user loan storage, and the EMI / amortisation engine, all on the server. It also serves the frontend from `public/`, so there is no CORS to set up.

## Run

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                     # http://localhost:3000
```

Open http://localhost:3000, sign up, log in, and use the Schedule generator.

Run the tests (standard library `unittest`, no extra packages):

```bash
python -m unittest discover -s tests -v
```

| Env var    | Default          | Purpose                                                   |
|------------|------------------|-----------------------------------------------------------|
| `PORT`     | `3000`           | HTTP port                                                 |
| `DB_FILE`  | `data/ledger.db` | SQLite file, created automatically                        |
| `APP_ENV`  | –                | Set to `production` to mark the cookie `Secure` (HTTPS)   |
| `HOST_PUBLIC` | –             | Set to `1` to listen on all interfaces instead of localhost only |

## Files

| File | Role |
|------|------|
| `app.py` | Flask app, routes, auth, error handling |
| `emi.py` | Amortisation engine (EMI, rate resets, rounding residue, due dates) |
| `loan_csv.py` | CSV parsing and row-level validation |
| `db.py` | SQLite schema and connection |
| `public/` | The frontend (only `app.js` was changed to call the API) |
| `tests/test_api.py` | Engine and API tests |

## API

JSON in and out. Auth uses an HttpOnly `sid` cookie.

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/api/signup` | `{name, email, pw}` → create account |
| POST | `/api/login` | `{email, pw}` → start session |
| POST | `/api/logout` | end session |
| GET | `/api/me` | current user (401 if not logged in) |
| POST | `/api/loans/import` | `{csv}` → validate and save loans (upsert by `loan_id`); 422 with row-level errors if the CSV is bad |
| GET | `/api/loans` | list your saved loans |
| GET | `/api/loans/<id>/schedule` | full schedule + summary |
| POST | `/api/loans/<id>/resets` | `{month, rate}` → add or replace a rate reset, returns the new schedule |
| DELETE | `/api/loans/<id>/resets/<month>` | remove a reset |
| DELETE | `/api/loans/<id>` | delete a loan |

## Behaviour notes

- Passwords are hashed with scrypt (salted). Session tokens are random and only their SHA-256 is stored. Login allows 10 failures per 15 minutes per IP + email.
- Every loan query is scoped to the logged-in user.
- The maths and rounding match the original frontend exactly: monthly interest rounds to the paisa and the last instalment absorbs the residue, so the closing balance is 0.00.
- Due dates clamp to month end (31 Jan + 1 month = 28/29 Feb); the original frontend rolled over into March.

## Before going live

- Run behind HTTPS and set `APP_ENV=production`.
- Don't use `python app.py` in production. Use a WSGI server, for example `gunicorn -w 3 -b 0.0.0.0:8000 "app:create_app()"`.
- The login throttle is per-process memory. With several workers or servers, move it to Redis or your database.
- SQLite is fine for a single server. For more, swap `db.py` and the SQL in `app.py` for Postgres.
