.PHONY: help install test lint format check build clean docs

help:
	@echo "Common targets:"
	@echo "  install   pip install -e .[dev] plus the tutor-plugin"
	@echo "  test      pytest with coverage gate"
	@echo "  lint      ruff check ."
	@echo "  format    ruff format ."
	@echo "  check     lint + format check + tests + makemigrations check"
	@echo "  build     sdist + wheel for both packages"
	@echo "  clean     remove build artifacts"

install:
	pip install --upgrade pip
	pip install -e ".[dev]"
	pip install -e ./tutor-plugin

test:
	pytest -v --cov --cov-report=term-missing --cov-fail-under=85

lint:
	ruff check .

format:
	ruff format .

check:
	ruff check .
	ruff format --check .
	python -m django makemigrations --check --dry-run --settings=settings --pythonpath=tests
	pytest -q --cov --cov-fail-under=85

build:
	rm -rf dist tutor-plugin/dist
	python -m build
	python -m build tutor-plugin

clean:
	rm -rf build dist *.egg-info tutor-plugin/dist tutor-plugin/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov .ruff_cache
