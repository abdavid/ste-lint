TOOL := tool
VENV := $(TOOL)/.venv
PY := $(VENV)/bin/python
MODEL_URL := https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

.PHONY: setup dictionary test doctor

setup:
	cd $(TOOL) && uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e $(TOOL)[dev]
	uv pip install --python $(PY) $(MODEL_URL)

dictionary:
	@test -n "$(PDF)" || (echo "usage: make dictionary PDF=path/to/asd-ste100-issue-9.pdf" && exit 2)
	$(TOOL)/bin/ste build-dictionary "$(PDF)"

test:
	cd $(TOOL) && .venv/bin/pytest -q

doctor:
	$(TOOL)/bin/ste doctor
