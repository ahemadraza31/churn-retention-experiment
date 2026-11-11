.PHONY: setup test health

setup:
	/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e .

test:
	.venv/bin/pytest -q

health:
	.venv/bin/python -m churnexp health --scale starter

