from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.consultation_lifecycle import (
    ACTIVE_CONSULTATION_STATUSES,
    assert_consultation_transition,
    normalize_consultation_status,
    validate_price_amount,
)


def expect_invalid_transition(current: str, target: str) -> None:
    try:
        assert_consultation_transition(current, target)
    except ValueError:
        return
    raise AssertionError(f"expected invalid transition {current} -> {target}")


def main() -> None:
    assert normalize_consultation_status("pending") == "requested"
    assert normalize_consultation_status("accepted") == "confirmed"
    assert normalize_consultation_status("in_progress") == "active"
    assert normalize_consultation_status("QUEUED") == "confirmed"
    assert normalize_consultation_status("ANSWERED") == "completed"

    assert "requested" in ACTIVE_CONSULTATION_STATUSES
    assert "confirmed" in ACTIVE_CONSULTATION_STATUSES
    assert "active" in ACTIVE_CONSULTATION_STATUSES

    assert_consultation_transition("requested", "pending_payment")
    assert_consultation_transition("requested", "confirmed")
    assert_consultation_transition("confirmed", "active")
    assert_consultation_transition("active", "completed")
    assert_consultation_transition("cancelled", "refunded")

    expect_invalid_transition("completed", "active")
    expect_invalid_transition("refunded", "confirmed")
    expect_invalid_transition("requested", "refunded")

    assert str(validate_price_amount("299.00")) == "299.00"
    for invalid in ["0", "-1", "100000.01", "12.345", "abc"]:
        try:
            validate_price_amount(invalid)
        except ValueError:
            continue
        raise AssertionError(f"expected invalid price: {invalid}")

    print("consultation_hardening_ok")


if __name__ == "__main__":
    main()
