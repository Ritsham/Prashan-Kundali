"""LLM Engine — Modular NLG layer for Kundali Studio.

Architecture:
    generator.py        Public entry point
    config.py           Provider selection & API key routing
    http_client.py      Raw HTTP POST helpers
    providers.py        One function per LLM provider
    prompts.py          System & user prompt construction (RAG pattern)
    context_builders.py Insight-to-prompt normalization helpers
    chart_scanners.py   Chart data analysis (yogas, aspects, combustion)
    archetype.py        Question archetype detection

Public API:
    generate_interpretation_answer(chart, interpretation) -> dict
"""
from app.llm_engine.generator import generate_interpretation_answer

__all__ = ["generate_interpretation_answer"]
