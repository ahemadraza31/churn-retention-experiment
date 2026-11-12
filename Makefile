.PHONY: setup test health demo app qa full

setup:
	/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e .

test:
	.venv/bin/pytest -q

health:
	.venv/bin/python -m churnexp health --scale starter

demo:
	.venv/bin/python -m churnexp all --scale starter
	.venv/bin/streamlit run app/streamlit_app.py

app:
	.venv/bin/streamlit run app/streamlit_app.py

qa:
	.venv/bin/python scripts/make_test_report.py

full:
	.venv/bin/python -m churnexp all --scale full
