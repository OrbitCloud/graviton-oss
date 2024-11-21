default: help


##@
##@ Initialize dev environment
##@

.PHONY: install
install: ##@ Install Poetry dependencies
	poetry install

.PHONY: install-precommit
install-precommit: ##@ Install pre-commit hooks
	pre-commit install

.PHONY: install-poly
install-poly: ##@ Install polylith plugins
	poetry self add poetry-multiproject-plugin
	poetry self add poetry-polylith-plugin


.PHONY: install-lego
install-lego: ##@ Install lego acme cli
	brew install lego


##@
##@ Local development
##@

.PHONY: stacks
stacks: ##@ Check for changes in stacks
	@./bin/drift_detect.sh

.PHONY: test
test: ##@ Run tests
	poetry run pytest --cov --cov-report=term-missing:skip-covered --junitxml=pytest.xml | tee pytest-coverage.txt

.PHONY: fmt
fmt: ##@ Ruff formatter and linter (autofix)
	poetry run ruff check --fix .
	poetry run ruff format .

.PHONY: lint
lint: ##@ Ruff formatter and linter (check mode)
	poetry run ruff check --no-fix .
	poetry run ruff format --check .

.PHONY: pyright
pyright: ##@ Run Pyright type checker
	poetry run pyright -p .

##@
##@ Scaffolding
##@

.PHONY: component
component: ##@ Create a new component
	copier copy templates/component_class .

.PHONY: base
base: ##@ Create a new base
	copier copy templates/base .

##@
##@ Dependency choirs
##@

.PHONY: outdated
outdated: ##@ Check for outdated Poetry dependencies
	poetry show --outdated --top-level

.PHONY: update
update: ##@ Update Poetry and pre-commit dependencies
	poetry update
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
