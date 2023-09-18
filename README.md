# Graviton SDK - Orbit's IaC library

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

## Development

```bash
# Install dependencies
make install

# Install pre-commit hooks
make install-precommit

# Run tests:
make test

# Run linters:
make lint

# Run lint formatters (automatically apply Black/isort):
make format

# Check outdated Python dependencies:
make outdated

# Update dependencies (runs poetry update and pre-commit autoupdate)
make update

```

- Structure based on [Polylith](https://polylith.gitbook.io/polylith/) & [python-polylith](https://github.com/DavidVujic/python-polylith).
