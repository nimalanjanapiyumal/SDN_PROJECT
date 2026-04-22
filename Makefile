PYTHON ?= python3

venv:
	$(PYTHON) -m venv .venv

install:
	. .venv/bin/activate && pip install -r requirements.txt

run:
	. .venv/bin/activate && uvicorn adaptive_cloud_platform.app:app --app-dir src --host 0.0.0.0 --port 8080

test:
	. .venv/bin/activate && pytest -q

package:
	bash scripts/package_release.sh v0.1.0
