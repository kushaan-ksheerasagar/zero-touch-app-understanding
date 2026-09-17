# Autonomous Exploration Agent (Phase 1)

This module implements the core decision brain for the autonomous app exploration system.

## Features in Phase 1

1. **Structured Screen Ingestion**: Ingests structured JSON/dict screen definitions containing `screen_id` and UI `elements`.
2. **Interactive Element Detection**: Filters elements based on `clickable: true`, element types (`button`, `input`, `checkbox`, etc.), and interactive actions.
3. **Exploration Memory**: Tracks visited screens and attempted elements per screen.
4. **Action Selection**:
   - Prioritizes unexplored interactive elements using `tap`.
   - Remembers previous actions and avoids re-attempting already explored elements on the same screen.
   - Automatically issues a `back` action once all interactive elements on the screen have been explored.
5. **Standardized Output**: Returns clean, machine-readable JSON actions.

## Supported Actions

- `tap`: Taps an interactive target element.
- `back`: Navigates backward when all interactive elements are explored.
- `scroll`: (Supported action type for future expansion).
- `wait`: (Supported action type for future expansion).
- `stop`: (Supported action type for future expansion).

---

## Directory Structure

```
agent/
├── __init__.py           # Package exports
├── types.py              # Action types and target definitions
├── memory.py             # ExplorationMemory for tracking screen visits and attempted elements
├── selector.py           # ActionSelector for determining interactive elements and picking actions
├── agent.py              # ExplorationAgent main entry point
├── demo.py               # Runnable step-by-step exploration simulation
├── README.md             # This documentation
└── tests/
    ├── __init__.py
    └── test_agent.py     # Unit tests
```

---

## Running the Tests

No external dependencies are required. Run tests using Python's built-in `unittest`:

From the project root:

```bash
python -m unittest discover -s agent/tests -p "test_*.py"
```

---

## Running the Demo

From the project root:

```bash
python -m agent.demo
```
