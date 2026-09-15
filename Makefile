.PHONY: install run debug test lint lint-strict clean

VENV := .venv
MAP ?= maps/medium/03_priority_puzzle.txt
ARGS ?= --visual

ifeq ($(OS),Windows_NT)
BIN := $(VENV)/Scripts
PYTHON := python
else
BIN := $(VENV)/bin
PYTHON := python3
endif

MYPY_FLAGS := --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	--disallow-untyped-defs --check-untyped-defs

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install parse flake8 mypy pytest

run:
	$(BIN)/python main.py $(MAP) $(ARGS)

debug:
	$(BIN)/python -m pdb main.py $(MAP) $(ARGS)

test:
	$(BIN)/python -m pytest -q

lint:
	$(BIN)/flake8 .
	$(BIN)/mypy . $(MYPY_FLAGS)

lint-strict:
	$(BIN)/flake8 .
	$(BIN)/mypy . --strict

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
