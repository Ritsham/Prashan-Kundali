"""Backward-compatibility shim.

The interpretation logic has been refactored into the modular
`app.insight_engine` package. This file re-exports everything so
any existing code that imports from `app.services.interpretation_service`
continues to work without changes.

New code should import directly from `app.insight_engine`.
"""
from app.insight_engine.core import *  # noqa: F401, F403
from app.insight_engine.rules.common import *  # noqa: F401, F403
from app.insight_engine.domains.marriage import *  # noqa: F401, F403
from app.insight_engine.domains.wealth import *  # noqa: F401, F403
from app.insight_engine.domains.education import *  # noqa: F401, F403
from app.insight_engine.domains.career import *  # noqa: F401, F403
from app.insight_engine.domains.illness import *  # noqa: F401, F403
from app.insight_engine.domains.foreign import *  # noqa: F401, F403
from app.insight_engine.domains.child import *  # noqa: F401, F403
