# Repository Guidelines

## Project Structure & Module Organization
RealityGuide's Python entry point is `main.py`, which houses the CLI surface today; keep feature-specific helpers in new modules under `src/` (create it if absent) and limit `main.py` to orchestration. Project metadata and dependency pins sit in `pyproject.toml` and `uv.lock`, while virtual-env artefacts stay in `.venv/` and cached analysis in `.ruff_cache/`. Place automated tests in `tests/` mirroring the module path (for example, `tests/test_main.py` exercises `main.py`).

## Build, Test, and Development Commands
- `uv sync` — install runtime and dev dependencies declared in `pyproject.toml`.
- `uv run python main.py` — execute the CLI locally; pass feature flags via standard arguments.
- `uv run ruff check .` — run linting and formatting fixes; prefer `--fix` only after reviewing the diff.
- `uv run basedpyright` — perform type analysis; treat new warnings as blockers.
- `uv run pytest -q` — execute the test suite once it exists; combine with `--maxfail=1` for fast feedback.

## Coding Style & Naming Conventions
Use Python 3.12+ features and 4-space indentation. Modules, functions, and variables follow `snake_case`, classes use `PascalCase`, and constants stay `UPPER_SNAKE_CASE`. Always add type hints at public boundaries. Keep functions below ~40 lines; factor helpers into `src/<feature>/utils.py`. Run Ruff before committing so formatting (import sorting, quote style) stays consistent.

## Testing Guidelines
Author tests with `pytest`, storing shared fixtures in `tests/conftest.py`. Name files `test_<module>.py` and individual cases `test_<behavior>`. Target at least 85% line coverage for new modules and cover both success and failure paths (e.g., invalid CLI args). For logic that depends on external APIs, stub requests with `pytest`'s monkeypatch to keep runs deterministic.

## Commit & Pull Request Guidelines
Match the existing history by using the `py: <imperative summary>` convention (for example, `py: add commute time parser`). Commits should be scope-focused and include updated docs/tests. Pull requests must describe the change, outline validation steps (commands + outcomes), link related issues, and attach screenshots or logs for CLI output when visuals help reviewers. Highlight breaking changes or new configuration requirements explicitly before requesting review.

## Security & Configuration Tips
Do not commit secrets or `.env` files; load credentials via environment variables at runtime. Treat `.venv/` as local-only and rely on `uv sync` for reproducible installs. When adding external libraries, justify them in the PR description and ensure licenses are compatible with the project. Validate user input at module boundaries so RealityGuide stays trustworthy for downstream agents.
