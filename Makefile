.PHONY: test lint outdated update flake8 isort pytest-cov pytest black pylint pyright

default: all

all:
	@make test
	@make lint

test:
	@make pytest-cov
	@make pytest

lint:
	@make isort-check
	@make black-check
	@make pyright
	@make pylint
	@make flake8

lint-fix:
	isort --profile=black .
	black .

outdated:
	poetry show --outdated --top-level

update:
	poetry update

flake8:
	flake8

isort-check:
	isort --check-only --profile=black .

black-check:
	black --check .

pytest-cov:
	pytest --cov=. --cov-report=term-missing

pytest:
	pytest -s --verbose test/

pylint:
	pylint --rcfile=.pylintrc --recursive yes .

pyright:
	pyright .