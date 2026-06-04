.PHONY: help install test lint format check build clean version-check \
	extract_translations compile_translations docs

help:
	@echo "Common targets:"
	@echo "  install                pip install -e .[dev] plus the tutor-plugin"
	@echo "  test                   pytest with coverage gate"
	@echo "  lint                   ruff check ."
	@echo "  format                 ruff format ."
	@echo "  check                  lint + format check + tests + makemigrations check + version sync"
	@echo "  build                  sdist + wheel for both packages"
	@echo "  extract_translations   django-admin makemessages -a"
	@echo "  compile_translations   django-admin compilemessages"
	@echo "  version-check          verify all version strings match"
	@echo "  clean                  remove build artifacts"

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

check: version-check
	ruff check .
	ruff format --check .
	python -m django makemigrations --check --dry-run --settings=settings --pythonpath=tests
	pytest -q --cov --cov-fail-under=85

version-check:
	@v1=$$(python -c "import course_inventory; print(course_inventory.__version__)"); \
	v2=$$(grep -E '^version = ' pyproject.toml | head -1 | awk -F'"' '{print $$2}'); \
	v3=$$(grep -E '^version = ' tutor-plugin/pyproject.toml | head -1 | awk -F'"' '{print $$2}'); \
	echo "course_inventory:                $$v1"; \
	echo "pyproject.toml:                  $$v2"; \
	echo "tutor-plugin/pyproject.toml:     $$v3"; \
	if [ "$$v1" != "$$v2" ] || [ "$$v2" != "$$v3" ]; then \
		echo "version drift — bump all three in lockstep"; exit 1; \
	fi

extract_translations:
	cd course_inventory && django-admin makemessages -a --no-location

compile_translations:
	cd course_inventory && django-admin compilemessages

build:
	rm -rf dist tutor-plugin/dist
	python -m build
	python -m build tutor-plugin

clean:
	rm -rf build dist *.egg-info tutor-plugin/dist tutor-plugin/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .coverage coverage.xml htmlcov .ruff_cache
