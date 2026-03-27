from __future__ import annotations

from ..models import LedgerShieldAction, LedgerShieldObservation
from ..openenv_compat import create_fastapi_app
from .environment import LedgerShieldEnvironment

env = LedgerShieldEnvironment()
app = create_fastapi_app(env, LedgerShieldAction, LedgerShieldObservation)
