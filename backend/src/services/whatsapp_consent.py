"""WhatsApp consent helpers — honor an inbound opt-out (STOP) by phone.

Used by the storefront BFF's WhatsApp webhook: when a customer replies STOP, the
BFF forwards the sender's phone here to clear their ``whatsapp_opt_in`` on the
customer master (LFPDPPP / WhatsApp policy require honoring opt-out).

Design notes:
  * We do NOT expose a phone→customer *lookup* (that would be a PII-enumeration
    oracle). This is an **action**: it finds matching customers and clears their
    consent, returning only a count.
  * Phone formats vary (``+52 55 1234 5678`` / ``5215512345678`` / ``5512345678``).
    We match on the **last 10 digits** (the MX national number) after stripping
    non-digits. Honoring a STOP is the safe direction, so on a match we opt out
    every matching customer record.
  * The candidate set is only customers who are currently opted in — a small,
    shrinking set — so this never scans the whole users table.
  * Never log the phone number.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models.user import User


def normalize_phone(phone: str | None) -> str:
    """Strip to digits and keep the last 10 (the national number). Empty if the
    input has fewer than 10 digits (too ambiguous to match safely)."""
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else ""


def opt_out_by_phone(db: Session, phone: str) -> int:
    """Clear ``whatsapp_opt_in`` for every opted-in customer matching ``phone``.

    Returns the number of customer records updated (0 when nothing matched — e.g.
    an unknown number or an already-opted-out customer). Idempotent.
    """
    target = normalize_phone(phone)
    if not target:
        return 0

    candidates = (
        db.query(User)
        .filter(
            User.user_type == "customer",
            User.whatsapp_opt_in.is_(True),
            User.phone.isnot(None),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    updated = 0
    for user in candidates:
        if normalize_phone(user.phone) == target:
            user.whatsapp_opt_in = False
            user.whatsapp_opt_in_at = now
            db.add(user)
            updated += 1

    if updated:
        db.commit()
    return updated
