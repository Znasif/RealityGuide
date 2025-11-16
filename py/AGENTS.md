## Project Overview
RealityGuide turns scene images into step-by-step manipulation guides for real-world assistants. Running `main.py` sends the scene through Gemini to infer a goal, list the key objects, and produce an ordered set of instructions. The script also crops out per-object close-ups, highlights the first object that should be addressed, and triggers a Gemini image generation pass that visualizes that initial action.

`check_completion.py` revisits the same workspace after actions have been taken. Given a fresh photo plus the previous plan, it marks finished steps, rewrites whatever still needs doing, and, if necessary, appends new actions to finish the original goal. It mirrors the initial run by calling attention to the next object to manipulate and refreshing the Gemini-generated visualization.

All of this is underpinned by `shared.py`, which defines the schemas for goals, objects, and steps while handling the common chores of resizing images, cropping object callouts, locating the right bounding box for a step, and dispatching the Gemini image generations.

## Commands
- `uv run --env-file .env main.py` — run the program
- `uv run ruff check --fix && uv run ruff format` — lint and format
- `uv run basedpyright` — run type checks
- `uv run python -c "print('hello')"` — run a Python

Run type checks, lint, and format after making any Python file changes.
