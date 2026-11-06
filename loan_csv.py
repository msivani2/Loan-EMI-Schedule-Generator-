"""CSV loan-master parsing and validation. Never raises on bad data; returns (loans, errors)."""
import csv
import io
import math
import re
from datetime import date

REQUIRED = ["loan_id", "borrower", "principal", "annual_rate", "tenure_months", "start_date"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def valid_date(s: str) -> bool:
    if not DATE_RE.match(s):
        return False
    try:
        date(*(int(p) for p in s.split("-")))
        return True
    except ValueError:
        return False


def to_number(v):
    """float or None (rejects blanks, NaN, inf, bools)."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        n = float(str(v).strip())
    except ValueError:
        return None
    return n if math.isfinite(n) else None


def parse_resets(text, tenure, errors, line):
    out = {}
    for part in filter(None, (text or "").split("|")):
        a, _, b = part.partition(":")
        month, rate = to_number(a), to_number(b)
        ok = (month is not None and month == int(month) and rate is not None
              and tenure is not None and 2 <= month <= tenure and 0 <= rate <= 100)
        if ok:
            out[int(month)] = rate
        else:
            errors.append(f'Row {line}: invalid reset "{part}" (month must be 2-{int(tenure or 0)}, rate 0-100)')
    return out


def parse_loan_csv(text: str):
    text = (text or "").lstrip("\ufeff")
    rows = [r for r in csv.reader(io.StringIO(text), skipinitialspace=True)
            if any(c.strip() for c in r)]
    if len(rows) < 2:
        return [], ["CSV needs a header row and at least one loan."]
    header = [h.strip().lower() for h in rows[0]]
    missing = [k for k in REQUIRED if k not in header]
    if missing:
        return [], [f"Missing column(s): {', '.join(missing)}"]
    body = rows[1:]
    if len(body) > 5000:
        return [], ["Too many loans in one file (max 5000)."]

    loans, errors, seen = [], [], set()
    for idx, r in enumerate(body):
        line = idx + 2
        o = {k: (r[i].strip() if i < len(r) else "") for i, k in enumerate(header)}
        before = len(errors)
        principal, rate, tenure_f = to_number(o["principal"]), to_number(o["annual_rate"]), to_number(o["tenure_months"])
        tenure = int(tenure_f) if tenure_f is not None and tenure_f == int(tenure_f) else None

        if not o["loan_id"]:
            errors.append(f"Row {line}: loan_id is required")
        elif o["loan_id"] in seen:
            errors.append(f"Row {line}: duplicate loan_id {o['loan_id']}")
        if not o["borrower"]:
            errors.append(f"Row {line}: borrower is required")
        if principal is None or not (0 < principal <= 1e10):
            errors.append(f"Row {line}: principal must be a positive number")
        if rate is None or not (0 <= rate <= 100):
            errors.append(f"Row {line}: annual_rate must be between 0 and 100")
        if tenure is None or not (1 <= tenure <= 600):
            errors.append(f"Row {line}: tenure_months must be a whole number from 1 to 600")
        if not valid_date(o["start_date"]):
            errors.append(f"Row {line}: start_date must be a real date as YYYY-MM-DD")
        resets = parse_resets(o.get("resets", ""), tenure, errors, line)
        seen.add(o["loan_id"])
        if len(errors) == before:
            loans.append({"id": o["loan_id"], "borrower": o["borrower"], "principal": principal,
                          "rate": rate, "tenure": tenure, "start": o["start_date"], "resets": resets})
    return loans, errors
