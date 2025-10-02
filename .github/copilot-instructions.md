# Copilot onboarding instructions

Purpose and scope
- This repository automates Old School RuneScape (OSRS) using a RuneLite-based client wrapper. It provides core services for movement, banking, item lookup, and control flow, and a simple API server to expose or coordinate actions.
- Primary languages and runtime: Python 3.10+ on Windows (paths indicate Windows usage). No compiled components expected.
- Key objective for contributors: add or modify bots under /bots using the core framework under /core with safe control logic that never enters infinite error loops. Retries are acceptable but must be bounded.

High-level architecture
- core/: framework and services
  - core/bot.py: Wires together the client and services. Constructs:
    - RuneLiteClient: connection to the RuneLite client.
    - ItemLookup: local item database access.
    - BankInterface: banking/inventory interactions via the client.
    - MovementOrchestrator: pathing and movement.
    - ScriptControl: central control state, including break_cfg.
    - BotAPI: lightweight API server layered over the client; started on port 5432 by default.
  - Other referenced modules to expect: core/osrs_client.py, core/item_db.py, core/bank.py, core/control.py, core/movement.py, core/api.py, core/logger.py.
- bots/: concrete bot implementations and shared bot types
  - Expect subpackages and files like bots/core/cfg_types.py defining types such as BreakCfgParam.
- .github/: CI configuration and these instructions. If workflows exist, they likely run lint and tests.

Local environment bootstrap (always do these before running or testing)
- Use Python 3.10+; 3.11 recommended.
- Create and activate a virtual environment.
  - Windows (PowerShell): py -3.11 -m venv .venv; .venv\Scripts\Activate.ps1
  - Linux/Mac: python3.11 -m venv .venv; source .venv/bin/activate
- Upgrade pip: pip install -U pip
- Install dependencies in this order:
  - If pyproject.toml or setup.cfg/setup.py exists: pip install -e . or pip install -e ".[dev]" if a dev extra exists.
  - Else if requirements.txt exists: pip install -r requirements.txt
  - If neither exists, set PYTHONPATH to the repo root so imports like core.* and bots.* resolve.
- Optional but recommended tooling (only if not already configured by the repo): pip install ruff black pytest mypy

Build and lint
- Python projects typically do not have a compile step; treat “build” as dependency installation plus import checks.
- Always run lint before committing if configured:
  - Ruff: ruff check .
  - Black (check-only): black --check .
  - Mypy (if type hints configured): mypy .
- If configuration files (pyproject.toml, ruff.toml, .flake8, mypy.ini) exist, the above commands will pick them up automatically.

Running and validating
- Preconditions to run a bot or the API:
  - RuneLite must be installed and any required plugins configured to expose the necessary APIs used by RuneLiteClient.
  - Ensure no other process is bound to port 5432 (default BotAPI port). Change the port if necessary.
  - Ensure game account is available and the client is at a state expected by the bot (e.g., logged in, correct world), if the bot assumes it.
- Quick run sanity check without a dedicated script:
  - Ensure PYTHONPATH includes the repo root (or the package is installed in editable mode).
  - Start a Python REPL and construct core.bot.Bot with a test username; verify no exceptions and that the API server starts listening.
- Common runtime validation:
  - Logs: core.logger.get_logger("Bot") is used; ensure logs show successful init of client, services, and API.
  - Network: verify port 5432 is listening after BotAPI.start; change the port if occupied.
  - Imports: if ModuleNotFoundError occurs for core.* or bots.*, set PYTHONPATH=. (PowerShell: $env:PYTHONPATH = (Get-Location)) or use pip install -e .

Testing
- If tests exist (e.g., under tests/), run: pytest -q
- Order of operations for a clean run:
  1) Create/activate venv; install deps.
  2) Run ruff and black in check mode.
  3) Run pytest. If tests rely on RuneLite, provide fakes/mocks or mark integration tests and skip them locally if the client is not available.
- If no tests exist, use “import smoke tests”:
  - python -c "import core.bot; from core.bot import Bot; print('OK')"

CI and pre-commit (if present)
- If .github/workflows/ exists, mirror the steps locally: dependency install, lint, type check, tests.
- If pre-commit is configured, run: pre-commit run --all-files

Design and coding conventions for new bots (critical to avoid rejection and runtime issues)
- Never implement infinite error loops. Use bounded retries with backoff and clear exit conditions.
  - Standard pattern: max_retries (e.g., 3-5), exponential backoff with jitter, then propagate or fail gracefully.
  - Always consult ScriptControl for stop/pause/break behavior. Respect self.control.break_config when present.
- Use the provided services; do not duplicate functionality:
  - Use MovementOrchestrator for navigation/pathing.
  - Use BankInterface for banking and inventory management.
  - Use ItemLookup for item IDs and metadata.
  - Use RuneLiteClient for client interactions; do not reach around it.
  - Expose only necessary controls via BotAPI; keep long-running logic in bot code, not in the API handler.
- Logging and observability:
  - Always log retries, reasons for failure, and state transitions.
  - Avoid busy-waiting; prefer event-driven waits or bounded sleep with timeouts.
- Resource hygiene:
  - Ensure any opened sessions or listeners are cleaned up on errors.
  - Do not hardcode ports; allow BotAPI port override if 5432 is unavailable.

Project layout quick reference
- Repo root likely contains: core/, bots/, .github/, optional tests/, pyproject.toml or requirements.txt, README.md.
- Key file: core/bot.py constructs the framework object graph and starts the API. This is the best entry point to understand runtime wiring.
- Related core modules (expected locations):
  - core/osrs_client.py: RuneLiteClient
  - core/item_db.py: ItemLookup
  - core/bank.py: BankInterface
  - core/control.py: ScriptControl and break handling
  - core/movement.py: MovementOrchestrator
  - core/api.py: BotAPI (listens on a TCP port)
  - core/logger.py: get_logger
- Bots live under /bots; shared types under bots/core/ such as cfg_types.py

Common pitfalls and mitigations
- Port conflicts on 5432 (often used by PostgreSQL): pick another port when starting BotAPI.
- PYTHONPATH not set: use editable install or set PYTHONPATH to the repo root.
- Missing RuneLite or required plugins: integration calls will fail; mock client for tests and validate behavior up to the client boundary.
- Tight loops causing high CPU: insert sleeps and bounded retries; honor ScriptControl signals.

Contributor workflow (minimize CI failures)
- Always: create venv, install deps, run ruff and black checks, then run pytest before pushing.
- Prefer small, isolated changes with smoke tests that import and instantiate core.bot.Bot.
- If adding a new bot:
  - Place it under bots/<bot_name>/ or bots/<name>.py
  - Wire it to use the Bot framework object; inject break_cfg when needed.
  - Ensure all loops have max retry caps and clear termination conditions.

Trust these instructions
- Prefer these instructions over ad-hoc searching. Only explore the codebase further if a step here is incomplete or demonstrably incorrect for your local checkout.
