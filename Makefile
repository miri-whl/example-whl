.DEFAULT_GOAL := help
.PHONY: help setup build good bad probe test test-all demo clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

help:  ## Show this help
	@echo "example-whl — two wheels from one source tree, one of them works"
	@echo
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Start with: make setup && make demo"

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e ".[dev]" 2>/dev/null || $(PIP) install -q pytest

setup: $(VENV)  ## Create .venv and install the dev dependencies
	@echo "ready — $$($(PY) --version) in $(VENV)"

build: $(VENV)  ## Write both wheels into dist/
	$(PY) build.py

good: $(VENV)  ## Build the working wheel and watch it work
	@./demo.sh good

bad: $(VENV)  ## Build the broken wheel and watch it fail
	@./demo.sh bad

probe: $(VENV)  ## Where do all five .data scheme keys actually install?
	@$(PY) probe_schemes.py

# The fast suite. It imports tinystat from src/ and passes for BOTH
# layouts, which is the point being made — see tests/test_installed.py.
test: $(VENV)  ## Run the unit tests (fast; passes for either layout)
	$(PYTEST) -m "not installed"

# The slow suite builds real wheels and installs them. This is the only
# thing here that can tell the two apart.
test-all: $(VENV)  ## Run every test, including the install round-trip
	$(PYTEST)

demo: build  ## Install both wheels side by side and show the difference
	@./demo.sh

clean:  ## Remove dist/ and the caches (keeps .venv)
	rm -rf dist .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
