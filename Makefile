.PHONY: install run debug lint lint-strict clean

MAP := maps/easy/01_linear_path.txt

install:
	uv venv
	uv pip install parse flake8 mypy pytest

run:
	uv run python main.py $(MAP)

debug:
	uv run python -m pdb main.py $(MAP)

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

clean:
	rm -rf __pycache__ tests/__pycache__ .mypy_cache .pytest_cache dist
