from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from types import SimpleNamespace
from .environment import LedgerShieldEnvironment

env = LedgerShieldEnvironment()
app = FastAPI(title="LedgerShield OpenEnv", version="0.1.0")

class StepRequest(BaseModel):
    action_type: str
    payload: dict = {}

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/reset")
def reset(seed: int | None = None) -> dict:
    obs = env.reset(seed=seed)
    return {
        "observation": obs.__dict__,
        "reward": 0.0,
        "done": False,
        "info": {"case_id": env.state.case_id},
    }

@app.post("/step")
def step(request: StepRequest) -> dict:
    # Wrap the request in a namespace to mimic the Action object the env expects
    action = SimpleNamespace(action_type=request.action_type, payload=request.payload)
    obs = env.step(action)
    return env.result_payload(obs)

@app.get("/state")
def state() -> dict:
    return env.state.__dict__