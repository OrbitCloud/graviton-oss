.PHONY: test lint outdated update flake8 isort pytest-cov pytest black pylint pyright

default: help

test:
	@make pytest-cov
	@make pytest

install:
	poetry install

install-precommit:
	pre-commit install

format:
	isort --profile=black .
	black .

outdated:
	poetry show --outdated --top-level

update:
	poetry update
	pre-commit autoupdate


.PHONY: test-cov
lint: ##@ Lint and type checks
	@make ruff-check

.PHONY: fmt
fmt: ##@ Ruff formatter and linter (autofix)
	poetry run ruff --fix .
	poetry run ruff format .

.PHONY: ruff-check
ruff-check: ##@ Ruff formatter (check mode)
	poetry run ruff check --no-fix .
	poetry run ruff format --check .


pytest-cov:
	pytest --cov=. --cov-report=term-missing

pytest:
	pytest -s --verbose test/

pyright:
	pyright .

.PHONY: help
help: ##@ (Default) Print listing of key targets with their descriptions
	@printf "\nUsage: make <command>\n"
	@grep -F -h "##@" $(MAKEFILE_LIST) | grep -F -v grep -F | sed -e 's/\\$$//' | awk 'BEGIN {FS = ":*[[:space:]]*##@[[:space:]]*"}; \
	{ \
		if($$2 == "") \
			printf ""; \
		else if($$0 ~ /^#/) \
			printf "\n%s\n", $$2; \
		else if($$1 == "") \
			printf "     %-20s%s\n", "", $$2; \
		else \
			printf "    \033[34m%-20s\033[0m %s\n", $$1, $$2; \
	}'
