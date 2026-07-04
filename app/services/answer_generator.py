"""Backward-compatibility shim.

The LLM generation logic has been refactored into the modular
`app.llm_engine` package. This file re-exports everything so any
existing code that imports from `app.services.answer_generator`
continues to work without changes.

New code should import directly from `app.llm_engine`.
"""
from app.llm_engine.generator import generate_interpretation_answer  # noqa: F401
from app.llm_engine.config import *  # noqa: F401, F403
from app.llm_engine.http_client import *  # noqa: F401, F403
from app.llm_engine.providers import *  # noqa: F401, F403
from app.llm_engine.prompts import *  # noqa: F401, F403
from app.llm_engine.context_builders import *  # noqa: F401, F403
from app.llm_engine.chart_scanners import *  # noqa: F401, F403
from app.llm_engine.archetype import *  # noqa: F401, F403
