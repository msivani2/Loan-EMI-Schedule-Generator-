"""Reducing-balance amortisation engine (same maths as the original frontend)."""
import calendar
import math
from datetime import date

EPS = 2.220446049250313e-16  # JS Number.EPSILON


def r2(x: float) -> float:
    # Same rounding as the frontend: Math.round((x + EPSILON) * 100) / 100 (halves round up)
    return math.floor((x + EPS) * 100 + 0.5) / 100


def emi(principal: float, annual_rate: float, n: int) -> float:
    r = annual_rate / 1200
    if r == 0:
        return r2(principal / n)
    f = math.pow(1 + r, n)
    return r2(principal * r * f / (f - 1))


def due_date(start: str, m: int) -> str:
    """start + m months, clamped to month end (31 Jan + 1 month -> 28/29 Feb)."""
    y, mo, d = (int(p) for p in start.split("-"))
    total = mo - 1 + m
    yy, mm = y + total // 12, total % 12 + 1
    dd = min(d, calendar.monthrange(yy, mm)[1])
    return date(yy, mm, dd).isoformat()


def build_schedule(loan: dict) -> list[dict]:
    """loan: principal, rate, tenure, start, resets {month: new_rate}"""
    bal, rate = loan["principal"], loan["rate"]
    e = emi(bal, rate, loan["tenure"])
    rows = []
    for m in range(1, loan["tenure"] + 1):
        is_reset = m in loan["resets"]
        if is_reset:
            rate = loan["resets"][m]
            e = emi(bal, rate, loan["tenure"] - m + 1)
        opening = bal
        interest = r2(bal * rate / 1200)
        last = m == loan["tenure"]
        principal = bal if last else r2(e - interest)
        pay = r2(principal + interest) if last else e
        bal = r2(bal - principal)
        rows.append({
            "month": m, "date": due_date(loan["start"], m), "rate": rate,
            "opening": opening, "emi": pay, "interest": interest,
            "principal": principal, "closing": bal,
            "isReset": is_reset, "isLast": last, "regularEmi": e,
        })
    return rows


def summarise(loan: dict, rows: list[dict]) -> dict:
    total_interest = r2(sum(r["interest"] for r in rows))
    return {
        "openingEmi": rows[0]["regularEmi"],
        "totalInterest": total_interest,
        "totalPayable": r2(loan["principal"] + total_interest),
        "resetCount": len(loan["resets"]),
        "finalAdjustment": r2(rows[-1]["emi"] - rows[0]["regularEmi"]),
    }
