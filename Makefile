.PHONY: help all venv install test cov lint fmt clean uv-venv uv-install uv-test

# Default interpreter (Homebrew Python 3.11)
PY?=/opt/homebrew/opt/python@3.11/bin/python3.11
UV?=uv
VENV=.venv
ACTIVATE=. $(VENV)/bin/activate

help:
	@echo "Targets:"
	@echo "  make all      - venv + install + lint + fmt + test"
	@echo "  make venv     - create venv using uv and $(PY)"
	@echo "  make install  - install project (editable + dev) using uv"
	@echo "  make test     - run pytest with coverage"
	@echo "  make uv-venv  - create venv using uv and $(PY)"
	@echo "  make uv-install - install deps with uv into .venv (editable + dev)"
	@echo "  make uv-test  - run pytest (uv-managed venv)"
	@echo "  make cov      - show coverage HTML report (opens htmlcov/index.html)"
	@echo "  make lint     - run mypy (if installed)"
	@echo "  make fmt      - run black formatting"
	@echo "  make clean    - remove venv and caches"

all: venv install lint fmt test

venv: uv-venv

install: uv-install

# Test with coverage; config comes from pyproject addopts
test:
	@$(ACTIVATE); pytest -q

cov:
	@$(ACTIVATE); pytest --cov=src --cov-report=html
	@open htmlcov/index.html || true

lint:
	@$(ACTIVATE); mypy src || true

fmt:
	@$(ACTIVATE); black src tests

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache htmlcov *.egg-info

# --------- uv (Astral) workflow ---------
# Requires: brew install uv
uv-venv:
	@if ! command -v $(UV) >/dev/null 2>&1; then echo "uv not found. Install with: brew install uv"; exit 1; fi
	@if [ ! -x "$(PY)" ]; then echo "Python not found at $(PY)"; exit 1; fi
	@if [ ! -d "$(VENV)" ]; then \
		$(UV) venv --python $(PY) $(VENV); \
	else \
		echo "Using existing $(VENV)"; \
	fi
	@$(UV) pip install -p $(VENV) --upgrade pip wheel

uv-install: uv-venv
	@$(UV) pip install -p $(VENV) -e '.[dev]'

uv-test:
	@. $(VENV)/bin/activate; pytest -q
