# Makefile for pySOF0273 project
# Targets:
#   make venv       -> create virtualenv .venv (if venv available)
#   make install    -> install requirements (venv or local fallback)
#   make test       -> run tests (using venv pytest or local fallback)
#   make precommit-install -> install pre-commit locally or in venv
#   make precommit-run     -> run pre-commit hooks on all files
#   make clean      -> remove virtualenv, local packages and caches
#   make clean-all  -> remove more artifacts

PYTHON ?= python3
VENV_DIR := .venv
LOCAL_PKGS := .local_packages
REQ := requirements.txt

.PHONY: help venv install test precommit-install precommit-run clean clean-all

help:
	@echo "Usage: make <target>"
	@echo "Targets: venv install test precommit-install precommit-run clean clean-all"

venv:
	@echo "Creating virtual environment if possible..."
	@$(PYTHON) -m venv $(VENV_DIR) 2>/dev/null || echo "venv module not available"
	@echo "Done (venv may or may not have been created)"

install: venv
	@echo "Installing requirements..."
	@if [ -d $(VENV_DIR) ]; then \
		$(VENV_DIR)/bin/pip install -r $(REQ); \
	else \
		$(PYTHON) -m pip install --upgrade --target $(LOCAL_PKGS) -r $(REQ); \
	fi

precommit-install: install
	@echo "Installing pre-commit..."
	@if [ -d $(VENV_DIR) ]; then \
		. $(VENV_DIR)/bin/activate && pip install -U pre-commit virtualenv; \
		. $(VENV_DIR)/bin/activate && pre-commit install; \
	else \
		$(PYTHON) -m pip install --upgrade virtualenv; \
		$(PYTHON) -m pip install --upgrade --target $(LOCAL_PKGS) pre-commit; \
		$(PYTHON) -c "import sys, os, runpy; sys.argv=['pre-commit','install']; sys.path.insert(0, os.path.join(os.getcwd(), '$(LOCAL_PKGS)')); runpy.run_module('pre_commit', run_name='__main__')"; \
	fi

precommit-run: precommit-install
	@echo "Running pre-commit hooks on all files..."
	@if [ -d $(VENV_DIR) ]; then \
		. $(VENV_DIR)/bin/activate && pre-commit run --all-files; \
	else \
		$(PYTHON) -c "import sys, os, runpy; sys.argv=['pre-commit','run','--all-files']; sys.path.insert(0, os.path.join(os.getcwd(), '$(LOCAL_PKGS)')); runpy.run_module('pre_commit', run_name='__main__')"; \
	fi

test:
	@echo "Running tests..."
	@if [ -d $(VENV_DIR) ]; then \
		PYTHONPATH=$(CURDIR):$(PYTHONPATH) $(VENV_DIR)/bin/pytest -q; \
	else \
		$(PYTHON) -c "import sys, os; sys.path.insert(0, os.path.join(os.getcwd(),'src')); sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), '$(LOCAL_PKGS)')); import pytest; sys.exit(pytest.main(['-q']))"; \
	fi

ci: install
	@echo "Running CI tests (junit xml output)..."
	@if [ -d $(VENV_DIR) ]; then \
		. $(VENV_DIR)/bin/activate && PYTHONPATH=$(CURDIR)/src:$(CURDIR):$(PYTHONPATH) pytest -q --junitxml=report.xml; \
	else \
		$(PYTHON) -c "import sys, os; sys.path.insert(0, os.path.join(os.getcwd(),'src')); sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), '$(LOCAL_PKGS)')); import pytest; sys.exit(pytest.main(['-q','--junitxml','report.xml']))"; \
	fi

clean:
	@echo "Cleaning common temporary files..."
	rm -rf $(VENV_DIR) $(LOCAL_PKGS) .pytest_cache build dist
	find . -type d -name '__pycache__' -exec rm -rf {} + || true
	rm -rf **/*.pyc || true

clean-all: clean
	@echo "Cleaning additional artifacts (if any)..."
	-rm -rf .mypy_cache .coverage htmlcov
	@echo "Done."
