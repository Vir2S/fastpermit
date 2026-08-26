.PHONY: install lint format format-check typecheck test build check clean

install:
	python -m pip install -e '.[dev]'

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy src/fastpermit

test:
	pytest --cov=fastpermit --cov-report=term-missing

build:
	python -m build
	python -m twine check dist/*

check: lint format-check typecheck test build

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache build dist htmlcov
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
