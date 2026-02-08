.PHONY: test

test:
	pytest

## Convenience targets (optional tooling)
## These are intentionally “best-effort”: if you don't have the tools installed,
## just skip these targets.
.PHONY: format lint

format:
	python -m black .

lint:
	python -m ruff check .
