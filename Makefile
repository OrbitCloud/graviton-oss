default: help


##@
##@ Initialize dev environment
##@

.PHONY: install
install: ##@ Install dependencies with uv
	uv sync

.PHONY: install-precommit
install-precommit: ##@ Install pre-commit hooks
	pre-commit install


##@
##@ Local development
##@

.PHONY: stacks
stacks: ##@ Check for changes in stacks
	@./bin/drift_detect.sh

.PHONY: test
test: ##@ Run tests
	uv run pytest --cov --cov-report=term-missing:skip-covered --junitxml=pytest.xml | tee pytest-coverage.txt

.PHONY: fmt
fmt: ##@ Ruff formatter and linter (autofix)
	uv run ruff check --fix .
	uv run ruff format .

.PHONY: lint
lint: ##@ Ruff formatter and linter (check mode)
	uv run ruff check --no-fix .
	uv run ruff format --check .

.PHONY: pyright
pyright: ##@ Run Pyright type checker
	uv run pyright -p .

##@
##@ Scaffolding
##@

.PHONY: component
component: ##@ Create a new component
	uv run copier copy templates/component_class .

.PHONY: base
base: ##@ Create a new base
	uv run copier copy templates/base .

##@
##@ Dependency chores
##@

.PHONY: outdated
outdated: ##@ Check for outdated dependencies
	uv tree --outdated

.PHONY: update
update: ##@ Update uv and pre-commit dependencies
	uv lock --upgrade
	pre-commit autoupdate


##@
##@ Help
##@

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
