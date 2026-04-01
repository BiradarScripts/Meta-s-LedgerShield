from __future__ import annotations

from models import LedgerShieldAction, LedgerShieldObservation
from openenv_compat import create_fastapi_app
from .environment import LedgerShieldEnvironment

env = LedgerShieldEnvironment()
app = create_fastapi_app(env, LedgerShieldAction, LedgerShieldObservation)

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()