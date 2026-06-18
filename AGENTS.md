1. Always use `uv` for Python environment management:
   - Prefer `uv venv` to create virtual environments.
   - Use `uv sync` to install dependencies from `pyproject.toml` or `uv.lock`.
   - Run any Python commands via `uv run` (e.g., `uv run python script.py`).

2. Enforce code cleanliness with Ruff:
   - After generating or modifying Python code, run `uv run ruff check --fix`.
   - Ensure no errors or warnings remain.
   - If issues are found, either auto-fix them (if safe) or report them to the user.

3. Only execute `git commit` under user's request.

