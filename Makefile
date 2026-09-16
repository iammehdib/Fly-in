.PHONY: install run debug package lint lint-strict clean

VENV := .venv

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install flake8 mypy build readchar rich blessed \
		just-playback svgwrite

run:
	$(VENV)/bin/python a_maze_ing.py config.txt

debug:
	$(VENV)/bin/python -m pdb a_maze_ing.py config.txt

lint:
	$(VENV)/bin/flake8 . --exclude=$(VENV)
	$(VENV)/bin/mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(VENV)/bin/flake8 . --exclude=$(VENV)
	$(VENV)/bin/mypy . --strict

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf dist/
