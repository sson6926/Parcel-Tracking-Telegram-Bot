from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.constants.enums import TrackingStatus
from app.models import Carrier, Tracking

logger = logging.getLogger(__name__)

SUPPORTED_CARRIERS: dict[str, str] = {
    "jtexpress": "JT Express",
    "shopeeexpress": "Shopee Express",
    "ghn": "Giao Hàng Nhanh",
}


def detect_carrier(tracking_code: str) -> str | None:
    """
    Auto-detect carrier from tracking code.

    Patterns:
    - Shopee Express : SPX* / SLS* / VN*
    - JT Express     : JT* or pure digits (10–15 chars)
    - GHN            : exactly 8 uppercase alphanumeric chars with ≥1 letter
    """
    code = tracking_code.strip().upper()

    if code.startswith(("SPX", "SLS", "VN")):
        return "shopeeexpress"

    if code.startswith("JT"):
        return "jtexpress"
    if code.isdigit() and 10 <= len(code) <= 15:
        return "jtexpress"

    if len(code) == 8 and code.isalnum() and any(c.isalpha() for c in code):
        return "ghn"

    return None


def is_valid_for_carrier(tracking_code: str, carrier_code: str) -> bool:
    """Validate tracking code format for a specific carrier."""
    code = tracking_code.strip().upper()
    carrier = carrier_code.strip().lower()

    if carrier == "shopeeexpress":
        return code.startswith(("SPX", "SLS", "VN"))

    if carrier == "jtexpress":
        if "-" in code:
            return True  # code-phone4digits format — let provider validate
        return code.startswith("JT") or (code.isdigit() and 10 <= len(code) <= 15)

    if carrier == "ghn":
        return len(code) == 8 and code.isalnum() and any(c.isalpha() for c in code)

    return True


def seed_carriers(session: Session) -> None:
    """Insert missing carriers and deactivate delivered trackings."""
    existing = {row[0] for row in session.execute(select(Carrier.code)).all()}
    for code, name in SUPPORTED_CARRIERS.items():
        if code not in existing:
            session.add(Carrier(code=code, name=name))
    session.execute(
        update(Tracking)
        .where(Tracking.last_status == TrackingStatus.DELIVERED.value)
        .values(is_active=False, next_check_at=None)
    )
    session.commit()
    logger.info("Carriers seeded: %s", list(SUPPORTED_CARRIERS.keys()))
