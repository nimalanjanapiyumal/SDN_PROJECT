PROJECT_ROOT := $(shell pwd)

install:
	bash scripts/install_ubuntu.sh

models:
	.venv/bin/python ml/train_models.py --samples 6000

up:
	bash scripts/start_all.sh

down:
	bash scripts/stop_all.sh

controller:
	bash scripts/start_controller.sh --foreground

policy:
	bash scripts/start_policy_agent.sh --foreground

topology:
	bash scripts/run_topology.sh --foreground --scenario mixed

test:
	.venv/bin/python -m pytest -q

clean:
	rm -f run/*.pid logs/*.log
