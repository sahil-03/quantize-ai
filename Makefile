# .PHONY: setup install clean test run venv activate deactivate tvm-env tvm-activate

# # Default Python interpreter
# PYTHON = python3
# VENV_NAME = venv
# VENV_DIR = $(CURDIR)/$(VENV_NAME)
# VENV_BIN = $(VENV_DIR)/bin
# VENV_ACTIVATE = $(VENV_BIN)/activate
# PYTHON_VENV = $(VENV_BIN)/python
# PIP_VENV = $(VENV_BIN)/pip

# # TVM-specific environment
# TVM_VENV_NAME = tvm_venv
# TVM_VENV_DIR = $(CURDIR)/$(TVM_VENV_NAME)
# TVM_VENV_BIN = $(TVM_VENV_DIR)/bin
# TVM_VENV_ACTIVATE = $(TVM_VENV_BIN)/activate
# PYTHON_TVM_VENV = $(TVM_VENV_BIN)/python
# PIP_TVM_VENV = $(TVM_VENV_BIN)/pip

# # Project directories
# SRC_DIR = core
# TEST_DIR = tests

# # Default target
# all: setup

# # Create virtual environment and install dependencies
# setup: venv install
# 	@echo "Setup complete. Activate the virtual environment with: source $(VENV_ACTIVATE)"

# # Create virtual environment if it doesn't exist
# venv:
# 	@echo "Creating virtual environment..."
# 	@if [ ! -d "$(VENV_DIR)" ]; then \
# 		$(PYTHON) -m venv $(VENV_DIR); \
# 		$(PIP_VENV) install --upgrade pip setuptools wheel; \
# 		echo "Virtual environment created at $(VENV_DIR)"; \
# 	else \
# 		echo "Virtual environment already exists at $(VENV_DIR)"; \
# 	fi

# # Activate virtual environment (note: this must be sourced, not executed)
# # Usage: source $(shell make --no-print-directory activate)
# activate:
# 	@echo "$(VENV_ACTIVATE)"

# # Create TVM-specific virtual environment
# tvm-env:
# 	@echo "Creating TVM-specific virtual environment..."
# 	@if [ ! -d "$(TVM_VENV_DIR)" ]; then \
# 		$(PYTHON) -m venv $(TVM_VENV_DIR); \
# 		$(PIP_TVM_VENV) install --upgrade pip setuptools wheel; \
# 		$(PIP_TVM_VENV) install numpy==1.23.0 cython; \
# 		echo "TVM virtual environment created at $(TVM_VENV_DIR)"; \
# 	else \
# 		echo "TVM virtual environment already exists at $(TVM_VENV_DIR)"; \
# 	fi

# # Install dependencies
# install: venv
# 	@echo "Installing dependencies..."
# 	$(PIP_VENV) install -r requirements.txt
# 	@echo "Dependencies installed"

# # Run tests
# test: venv
# 	@echo "Running tests..."
# 	$(PYTHON_VENV) -m unittest discover -s $(TEST_DIR)

# # Run the application
# run: venv
# 	@echo "Running application..."
# 	$(PYTHON_VENV) -m $(SRC_DIR).inference_scripts.llama_inference

# # Clean up
# clean:
# 	@echo "Cleaning up..."
# 	rm -rf __pycache__ .pytest_cache
# 	find . -type d -name __pycache__ -exec rm -rf {} +
# 	find . -type f -name "*.pyc" -delete
# 	@echo "Cleaned up generated files"

# # Deep clean (including virtual environments)
# clean-all: clean
# 	@echo "Removing virtual environments..."
# 	rm -rf $(VENV_DIR) $(TVM_VENV_DIR)
# 	@echo "Virtual environments removed"

# # Help
# help:
# 	@echo "Available targets:"
# 	@echo "  setup         - Create main virtual environment and install dependencies"
# 	@echo "  venv          - Create main virtual environment only"
# 	@echo "  activate      - Print command to activate main virtual environment (use with source)"
# 	@echo "  tvm-env       - Create TVM-specific virtual environment with numpy==1.23.0"
# 	@echo "  tvm-activate  - Print command to activate TVM virtual environment (use with source)"
# 	@echo "  install-tvm   - Install TVM from source in the TVM-specific environment"
# 	@echo "  install       - Install dependencies in the main environment"
# 	@echo "  test          - Run tests"
# 	@echo "  run           - Run the application"
# 	@echo "  clean         - Clean up generated files"
# 	@echo "  clean-all     - Clean up everything including virtual environments"
# 	@echo ""
# 	@echo "Usage example for main environment:"
# 	@echo "  make setup              # Set up main environment"
# 	@echo "  source \$$(make activate) # Activate the main environment"
# 	@echo ""
# 	@echo "Usage example for TVM:"
# 	@echo "  make tvm-env                # Create TVM environment"
# 	@echo "  source \$$(make tvm-activate) # Activate TVM environment"
# 	@echo "  make install-tvm            # Install TVM in the TVM environment"



.PHONY: venv install clean test lint format help

PYTHON := python3
VENV_NAME := venv
VENV_ACTIVATE := $(VENV_NAME)/bin/activate
PYTHON_VENV := $(VENV_NAME)/bin/python

help:
	@echo "make venv        - Create a virtual environment"
	@echo "make install     - Install production dependencies"
	@echo "make test        - Run tests"
	@echo "make lint        - Run linting checks"
	@echo "make format      - Format code"
	@echo "make clean       - Clean up build artifacts and virtual environment"

venv:
	$(PYTHON) -m venv $(VENV_NAME)

install: venv
	. $(VENV_ACTIVATE) && pip install -U pip setuptools wheel && pip install -e .

test: dev-install
	. $(VENV_ACTIVATE) && pytest --cov=your_project_name tests/

lint: dev-install
	. $(VENV_ACTIVATE) && flake8 your_project_name tests
	. $(VENV_ACTIVATE) && mypy your_project_name

format: dev-install
	. $(VENV_ACTIVATE) && black your_project_name tests
	. $(VENV_ACTIVATE) && isort your_project_name tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf $(VENV_NAME)
	find . -type d -name __pycache__ -exec rm -rf {} +