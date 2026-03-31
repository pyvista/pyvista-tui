# List available recipes
default:
    @just --list

# Sync the virtual environment and install the package
sync:
    uv sync --extra dev

# Delete and recreate the virtual environment
reset:
    rm -rf .venv
    uv sync --extra dev

# Run all tests with coverage
test *args:
    uv run pytest -vv tests/ --cov {{ args }}

# Run type checking
typecheck:
    uv run mypy pyvista_tui

# Run all linters and formatters (pre-commit hooks)
lint:
    uvx pre-commit run --all-files

# Run an example by name
example name="sphere":
    uv run python examples/{{ name }}.py
