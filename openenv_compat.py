from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Generic, Optional, TypeVar

try:  # pragma: no cover - used when openenv-core is installed
    from openenv.core import EnvClient, StepResult
    from openenv.core.env_server import Action, Environment, Observation, State, create_fastapi_app
except (ImportError, ModuleNotFoundError):  # pragma: no cover - local fallback
    # Defer importing optional runtime dependencies (httpx, fastapi, pydantic)
    # until they are actually needed. This makes it possible to run offline
    # artifact generation and tests in minimal environments without installing
    # the full web stack.

    @dataclass
    class Action:
        """Fallback Action base class."""

    @dataclass
    class Observation:
        """Fallback Observation base class."""

    @dataclass
    class State:
        episode_id: str = ""
        step_count: int = 0

    class Environment:
        """Fallback Environment base class."""
        pass

    ObsT_co = TypeVar("ObsT_co")

    @dataclass
    class StepResult(Generic[ObsT_co]):
        observation: Any
        reward: float = 0.0
        done: bool = False
        info: dict[str, Any] = field(default_factory=dict)

    ActT = TypeVar("ActT", bound=Action)
    ObsT = TypeVar("ObsT", bound=Observation)
    StateT = TypeVar("StateT", bound=State)

    class EnvClient(Generic[ActT, ObsT, StateT]):
        """
        Minimal fallback client compatible with the subset of the OpenEnv API
        used by this package.
        """

        def __init__(self, base_url: str):
            self.base_url = base_url.rstrip("/")
            self._client: Optional[httpx.Client] = None

        def _ensure_client(self) -> "httpx.Client":
            # Import httpx lazily to avoid hard dependency at module import time.
            try:
                import httpx
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError("httpx is required for EnvClient network operations") from exc
            if self._client is None:
                self._client = httpx.Client(base_url=self.base_url, timeout=30.0)
            return self._client

        def close(self) -> None:
            if self._client is not None:
                self._client.close()
                self._client = None

        def __enter__(self):
            self._ensure_client()
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()
            return False

        def sync(self):
            return self

        def reset(self, seed: int | None = None, case_id: str | None = None, track: str | None = None):
            client = self._ensure_client()
            payload = {"seed": seed, "case_id": case_id, "track": track}
            response = client.post("/reset", json=payload)
            response.raise_for_status()
            return self._parse_result(response.json())

        def step(self, action: ActT):
            client = self._ensure_client()
            response = client.post("/step", json=self._step_payload(action))
            response.raise_for_status()
            return self._parse_result(response.json())

        def state(self) -> StateT:
            client = self._ensure_client()
            response = client.get("/state")
            response.raise_for_status()
            return self._parse_state(response.json())

        @classmethod
        def from_docker_image(
            cls,
            image_name: str,
            base_url: str = "http://localhost:8000",
        ):
            del image_name
            return cls(base_url=base_url)

        def _step_payload(self, action: ActT) -> dict[str, Any]:
            raise NotImplementedError

        def _parse_result(self, payload: dict[str, Any]) -> StepResult[ObsT]:
            raise NotImplementedError

        def _parse_state(self, payload: dict[str, Any]) -> StateT:
            raise NotImplementedError

    def _serialize(value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        return value

    def create_fastapi_app(env: Any, action_cls: Any, observation_cls: Any) -> "FastAPI":
        # Import FastAPI and Pydantic lazily so the module can be imported in
        # lightweight environments where the web stack isn't installed.
        try:
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError("fastapi and pydantic are required to create the server app") from exc

        app = FastAPI(title="LedgerShield OpenEnv", version="0.3.0")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/")
        def root() -> dict[str, Any]:
            return {
                "status": "ok",
                "service": "LedgerShield OpenEnv",
            }

        @app.get("/health")
        def health() -> dict[str, Any]:
            return {"status": "ok"}

        @app.post("/reset")
        def reset(request: dict[str, Any]) -> dict[str, Any]:
            seed = request.get("seed") if request else None
            case_id = request.get("case_id") if request else None
            track = request.get("track") if request else None
            obs = env.reset(seed=seed, case_id=case_id, track=track)

            if hasattr(env, "result_payload"):
                return env.result_payload(obs)

            return {
                "observation": _serialize(obs),
                "reward": 0.0,
                "done": False,
                "info": {},
            }

        @app.post("/step")
        def step(request: dict[str, Any]) -> dict[str, Any]:
            action = action_cls(**request)
            obs = env.step(action)

            if hasattr(env, "result_payload"):
                return env.result_payload(obs)

            return {
                "observation": _serialize(obs),
                "reward": 0.0,
                "done": False,
                "info": {},
            }

        @app.get("/state")
        def state() -> dict[str, Any]:
            if hasattr(env, "public_state"):
                return _serialize(env.public_state())
            current_state = env.state
            if is_dataclass(current_state):
                return asdict(current_state)
            return current_state

        return app

__all__ = [
    "Action",
    "Observation",
    "State",
    "Environment",
    "EnvClient",
    "StepResult",
    "create_fastapi_app",
]
