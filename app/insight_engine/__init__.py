"""Insight Engine — Rule-based astrological interpretation layer.

Architecture:
    core.py              Public entry point + domain routing
    rules/common.py      Shared helpers (planet strength, yogas, timing)
    domains/marriage.py  Prashna rules for marriage/relationship
    domains/wealth.py    Prashna rules for wealth/money
    domains/education.py Prashna rules for education/exams
    domains/career.py    Prashna rules for government & private jobs
    domains/illness.py   Prashna rules for health/illness
    domains/foreign.py   Prashna rules for foreign travel/settlement
    domains/child.py     Prashna rules for child/progeny

Public API:
    build_interpretation(chart) -> dict | None
"""
from app.insight_engine.core import build_interpretation

__all__ = ["build_interpretation"]
