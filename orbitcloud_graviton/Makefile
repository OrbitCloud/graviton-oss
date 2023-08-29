.PHONY: test

pre:
	poetry run pulumi preview --refresh

prediff:
	poetry run pulumi preview --refresh --diff

up:
	poetry run pulumi up --refresh

updiff:
	poetry run pulumi up --refresh --diff

select:
	poetry run pulumi stack select

ls:
	poetry run pulumi stack ls

output:
	poetry run pulumi stack output

destroy:
	poetry run pulumi destroy

test-cov:
	poetry run pytest --cov=orbitcloud_graviton --cov-report=term-missing

test:
	poetry run pytest -s --verbose test/

# test:
# 	@make test-black
# 	@make test-pylint
# 	@make test-mypy
# 	@make test-pytest-cov

test-black:
	poetry run black --check .

test-pylint:
	poetry run pylint --rcfile=pylintrc .

test-mypy:
	poetry run mypy --config-file=mypy.ini .
