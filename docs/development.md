# Development Guide

Guide for developers contributing to LedgerShield.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Docker (optional, for containerized development)
- Make (optional, for convenience commands)

### Clone Repository

```bash
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield
```

### Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip
```

### Install Dependencies

```bash
# Install package in development mode
pip install -e .

# Install test dependencies
pip install -r requirements.txt
```

### Verify Installation

```bash
# Run tests
python -m pytest tests/ -q

# Validate environment
openenv validate
```

## Project Structure

```
Meta-s-LedgerShield/
├── server/                    # FastAPI server and environment
│   ├── app.py                # FastAPI entrypoint
│   ├── environment.py        # Core environment
│   ├── world_state.py        # State management
│   ├── tools.py              # Investigation tools
│   ├── grading.py            # Task grading
│   ├── trajectory_grading.py # Trajectory scoring
│   ├── outcome_simulator.py  # Outcome simulation
│   ├── transition_engine.py  # Action processing
│   ├── risk_rules.py         # Risk assessment
│   ├── vendor_simulator.py   # Callback simulation
│   ├── pressure_events.py    # Pressure events
│   ├── data_loader.py        # Fixture loading
│   ├── case_factory.py       # Case generation
│   ├── attack_library.py     # Attack patterns
│   ├── schema.py             # Shared utilities
│   └── fixtures/             # Test data
│       ├── cases.json
│       ├── vendors.json
│       ├── po_records.json
│       ├── receipts.json
│       ├── ledger_index.json
│       ├── email_threads.json
│       ├── policy_rules.json
│       └── vendor_history.json
├── docs/                      # Documentation
├── tests/                     # Test suite
│   ├── test_ledgershield_env.py
│   ├── test_api_smoke.py
│   └── ...
├── models.py                  # Data models
├── inference.py               # Baseline agent
├── client.py                  # HTTP client
├── openenv_compat.py          # OpenEnv compatibility
├── benchmark_report.py        # Benchmark reporting
├── validate_grader.py         # Grader validation
├── Dockerfile                 # Container config
├── pyproject.toml            # Package config
└── openenv.yaml              # OpenEnv metadata
```

## Development Workflow

### Running the Server

```bash
# Development mode
python -m server.app

# With custom port
PORT=8001 python -m server.app

# With hot reload (for development)
uvicorn server.app:app --reload --port 8000
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_ledgershield_env.py -v

# Run specific test
python -m pytest tests/test_ledgershield_env.py::test_reset -v

# Run with coverage
python -m pytest --cov=server --cov-report=html

# Run benchmarks
python -m pytest --benchmark-only
```

### Code Quality

```bash
# Format code (if using black)
black server/ tests/ *.py

# Lint (if using flake8)
flake8 server/ tests/

# Type check (if using mypy)
mypy server/
```

## Making Changes

### Adding a New Tool

1. **Add tool function** in `server/tools.py`:

```python
def my_new_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Description of what the tool does."""
    # Implementation
    return {
        "success": True,
        "data": {...},
        "message": "Tool completed successfully."
    }
```

2. **Add to ALLOWED_ACTIONS** in `server/schema.py`:

```python
ALLOWED_ACTIONS = [
    # ... existing actions
    "my_new_tool",
]
```

3. **Add tool cost** in `server/environment.py`:

```python
TOOL_COSTS = {
    # ... existing costs
    "my_new_tool": 0.25,
}
```

4. **Add dispatch** in `server/environment.py`:

```python
def _dispatch_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    # ... existing tools
    if tool_name == "my_new_tool":
        return my_new_tool(self.current_case, payload)
```

5. **Add tests** in `tests/test_ledgershield_env.py`:

```python
def test_my_new_tool():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")
    
    action = LedgerShieldAction(
        action_type="my_new_tool",
        payload={"param": "value"}
    )
    obs = env.step(action)
    
    assert obs.last_tool_result["success"]
```

### Adding a New Case

1. **Add case to** `server/fixtures/cases.json`:

```json
{
  "case_id": "CASE-F-001",
  "task_type": "task_f",
  "difficulty": "medium",
  "budget_total": 15.0,
  "max_steps": 20,
  "instruction": "New task instructions...",
  "documents": [...],
  "gold": {...}
}
```

2. **Add gold labels** appropriate for the task type

3. **Add test** in `tests/test_ledgershield_env.py`

4. **Update task documentation** in `docs/tasks.md`

### Modifying Grading

1. **Update grading logic** in `server/grading.py`

2. **Update score composition** in documentation

3. **Run validation**:

```bash
python validate_grader.py
```

4. **Update tests** to reflect new scoring

## Testing Strategy

### Test Categories

#### Unit Tests

Test individual functions in isolation:

```python
def test_field_score():
    pred = {"vendor": "Acme", "amount": 100}
    gold = {"vendor": "Acme", "amount": 100}
    assert field_score(pred, gold) == 1.0
```

#### Integration Tests

Test component interactions:

```python
def test_end_to_end_episode():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-A-001")
    
    # Take several actions
    for action in action_sequence:
        obs = env.step(action)
    
    # Submit decision
    final_obs = env.step(submit_action)
    assert final_obs.last_tool_result["final_score"] > 0.8
```

#### API Tests

Test HTTP endpoints:

```python
def test_reset_endpoint(client):
    response = client.post("/reset", json={"case_id": "CASE-A-001"})
    assert response.status_code == 200
    assert response.json()["case_id"] == "CASE-A-001"
```

### Test Fixtures

Use pytest fixtures for common setup:

```python
@pytest.fixture
def environment():
    env = LedgerShieldEnvironment()
    yield env

@pytest.fixture
def reset_env(environment):
    environment.reset(case_id="CASE-A-001")
    yield environment
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import Mock, patch

def test_with_mocked_llm():
    with patch('inference.get_model_assessment') as mock:
        mock.return_value = {"counterfactual": "Would PAY if..."}
        result = run_episode(...)
        assert result["success"]
```

## Debugging

### Enable Debug Logging

```bash
export LEDGERSHIELD_DEBUG=1
python inference.py
```

### Add Debug Prints

```python
def step(self, action):
    if os.getenv("LEDGERSHIELD_DEBUG") == "1":
        print(f"DEBUG: action={action}")
        print(f"DEBUG: state={self._state}")
```

### Use PDB

```python
import pdb; pdb.set_trace()
```

### Inspect State

```python
# In tests or debugging
env = LedgerShieldEnvironment()
env.reset(case_id="CASE-D-001")

# Access hidden world (testing only)
print(env._hidden_world)

# Access public state
print(env.public_state())
```

## Performance Profiling

### Time Profiling

```python
import time

start = time.time()
result = env.step(action)
print(f"Step took {time.time() - start:.2f}s")
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Run with profiling
python -m memory_profiler server/app.py
```

## Common Issues

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'server'`

**Solution**: Ensure you're in the repo root and PYTHONPATH is set:

```bash
export PYTHONPATH=/path/to/Meta-s-LedgerShield:$PYTHONPATH
```

### Port Already in Use

**Problem**: `Address already in use`

**Solution**: Use a different port:

```bash
PORT=8001 python -m server.app
```

### Test Failures

**Problem**: Tests failing with fixture errors

**Solution**: Clear pytest cache:

```bash
python -m pytest --cache-clear
```

### Case Not Found

**Problem**: `ValueError: unknown case_id`

**Solution**: Check `server/fixtures/cases.json` for valid case IDs

## Best Practices

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public functions
- Keep functions focused and small

### Documentation

- Update docs when changing behavior
- Add examples for new features
- Keep API reference in sync with code

### Testing

- Write tests for new features
- Maintain test coverage above 80%
- Test edge cases and error conditions
- Use descriptive test names

### Version Control

- Make atomic commits
- Write clear commit messages
- Use feature branches for changes
- Rebase before merging

## Release Process

1. **Update version** in `pyproject.toml`

2. **Update CHANGELOG.md**

3. **Run full test suite**:

```bash
python -m pytest
python validate_grader.py
openenv validate
```

4. **Create git tag**:

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

5. **Build and publish** (if applicable):

```bash
python -m build
twine upload dist/*
```

## Resources

- [Python Documentation](https://docs.python.org/3.11/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [OpenEnv Specification](https://github.com/openenv/spec)

## Getting Help

- Check [documentation](./index.md)
- Search [existing issues](https://github.com/BiradarScripts/Meta-s-LedgerShield/issues)
- Ask in [discussions](https://github.com/BiradarScripts/Meta-s-LedgerShield/discussions)
- Create new issue with reproduction steps
