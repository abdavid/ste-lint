TOOL := tool
VENV := $(TOOL)/.venv
PY := $(VENV)/bin/python
DATA := $(TOOL)/ste_lint/data
MODEL_URL := https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
DEST ?= $(HOME)/.claude/skills/ste-lint
PDF_URL := https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf
PDF_FILE := $(DATA)/asd-ste100-issue-9.pdf

.PHONY: setup dictionary download test doctor install

setup:
	test -x $(PY) || (cd $(TOOL) && uv venv --python 3.12 .venv)
	uv pip install --python $(PY) -e $(TOOL)[dev]
	uv pip install --python $(PY) $(MODEL_URL)

dictionary:
	@test -n "$(PDF)" || (echo "usage: make dictionary PDF=path/to/asd-ste100-issue-9.pdf" && exit 2)
	$(TOOL)/bin/ste build-dictionary "$(PDF)"

# Download ASD-STE100 Issue 9 from the official ASD-STE100 website for the
# user's own use (asks first; YES=1 skips the question), then build from it.
download:
	@command -v pdftotext >/dev/null || { echo "pdftotext not found: brew install poppler (or apt install poppler-utils)"; exit 2; }
	@echo "ASD-STE100 is copyright ASD (Brussels) and an EU trade mark of ASD. ste-lint is not"
	@echo "affiliated with ASD. This downloads Issue 9 from the official website"
	@echo "  $(PDF_URL)"
	@echo "for your own use. Do not share the PDF or the files built from it. ASD prefers that"
	@echo "you register through its free download form, which tells it how STE is used:"
	@echo "  https://www.asd-europe.org/standards-specifications/simplified-technical-english/download-asd-ste-100"
	@if [ "$(YES)" != 1 ]; then \
	  printf 'Download it now? [y/N] '; read answer || answer=; \
	  case "$$answer" in y|Y|yes|Yes) ;; *) echo "Cancelled (pass YES=1 to skip the question)."; exit 1 ;; esac; \
	fi
	curl -fL --proto '=https' --tlsv1.2 --progress-bar -o "$(PDF_FILE).part" "$(PDF_URL)"
	@test "$$(head -c 5 "$(PDF_FILE).part")" = "%PDF-" || { rm -f "$(PDF_FILE).part"; echo "The download is not a PDF."; exit 2; }
	@mv "$(PDF_FILE).part" "$(PDF_FILE)"
	@echo "Saved $(PDF_FILE) (gitignored)."
	$(MAKE) --no-print-directory dictionary PDF="$(PDF_FILE)"

test:
	cd $(TOOL) && .venv/bin/pytest -q

doctor:
	$(TOOL)/bin/ste doctor

# Install (or update) the Claude Code skill at DEST as a clean clone of this
# checkout, then build its dictionary from PDF, or reuse the one built here.
install:
	@set -e; \
	home() { case "$$1" in "~") echo "$$HOME" ;; "~/"*) echo "$$HOME/$${1#\~/}" ;; *) echo "$$1" ;; esac; }; \
	command -v uv >/dev/null || { echo "uv not found: brew install uv (or see https://docs.astral.sh/uv/)"; exit 2; }; \
	src="$$(pwd -P)"; dest="$$(home '$(DEST)')"; pdf=""; \
	if [ -n '$(PDF)' ]; then \
	  pdf="$$(home '$(PDF)')"; \
	  [ -f "$$pdf" ] || { echo "PDF not found: $$pdf"; exit 2; }; \
	  pdf="$$(cd "$$(dirname "$$pdf")" && pwd -P)/$$(basename "$$pdf")"; \
	fi; \
	if [ -d "$$dest/.git" ]; then \
	  if [ "$$(cd "$$dest" && pwd -P)" != "$$src" ]; then \
	    echo "Updating $$dest"; \
	    git -C "$$dest" pull --ff-only --quiet || \
	      { echo "Cannot update $$dest (no upstream, or local changes). Remove it and run make install again."; exit 2; }; \
	  fi; \
	elif [ -e "$$dest" ]; then \
	  echo "$$dest exists and is not a git checkout; remove it or pass DEST=..."; exit 2; \
	else \
	  echo "Installing to $$dest"; mkdir -p "$$(dirname "$$dest")"; \
	  git clone --quiet "$$src" "$$dest"; \
	  url="$$(git remote get-url origin 2>/dev/null || true)"; \
	  if [ -n "$$url" ]; then git -C "$$dest" remote set-url origin "$$url"; fi; \
	fi; \
	echo "Setting up the virtualenv and spaCy model (the first run downloads dependencies)"; \
	$(MAKE) --no-print-directory -C "$$dest" setup >/dev/null 2>&1 || \
	  { echo "setup failed; run: make -C $$dest setup"; exit 1; }; \
	if [ -n "$$pdf" ]; then \
	  $(MAKE) --no-print-directory -C "$$dest" dictionary PDF="$$pdf"; \
	elif [ "$$dest" != "$$src" ] && [ ! -f "$$dest/$(DATA)/dictionary.json" ] && [ -f "$(DATA)/dictionary.json" ]; then \
	  for f in dictionary.json rules.json build-report.json; do \
	    if [ -f "$(DATA)/$$f" ]; then cp "$(DATA)/$$f" "$$dest/$(DATA)/"; fi; \
	  done; \
	  echo "Reused the dictionary built in this checkout."; \
	fi; \
	if "$$dest/tool/bin/ste" doctor >/dev/null; then \
	  echo "ste-lint is ready: $$dest/tool/bin/ste"; \
	else \
	  echo "Installed, but the dictionary is not built yet. Run one of:"; \
	  echo "  make -C $$dest download            (fetches the PDF from the official ASD-STE100 website)"; \
	  echo "  make -C $$dest dictionary PDF=path/to/asd-ste100-issue-9.pdf"; \
	fi
