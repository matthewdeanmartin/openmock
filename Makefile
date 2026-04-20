# if you wrap everything in uv run, it runs slower.
ifeq ($(origin VIRTUAL_ENV),undefined)
    VENV := uv run
else
    VENV :=
endif

uv.lock: pyproject.toml
	@echo "Installing dependencies"
	@uv sync --all-extras


# tests can't be expected to pass if dependencies aren't installed.
# tests are often slow and linting is fast, so run tests on linted code.
test: pylint bandit uv.lock
	@echo "Running unit tests"
	$(VENV) py.test tests --cov=openmock --cov-report=html --cov-fail-under 85

test-real: uv.lock
	@echo "Running parity tests against Docker OpenSearch"
	uv run python scripts/opensearch_docker.py test

test-mock: uv.lock
	@echo "Running mock-backend-only tests"
	uv run python -m pytest tests -m mock_backend

test-parity: uv.lock
	@echo "Running parity tests against the in-memory backend"
	uv run python -m pytest tests -m parity


black:
	@echo "Formatting code"
	$(VENV) black .


pre-commit:  black
	@echo "Pre-commit checks"
	$(VENV) pre-commit run --all-files

.PHONY: pre-commit
pre-commit: pre-commit

bandit:  
	@echo "Security checks"
	$(VENV)  bandit openmock -r


pylint:  black
	@echo "Linting with pylint"
	$(VENV) pylint openmock --fail-under 10


check: test pylint bandit pre-commit

.PHONY: build
build: check
	$(VENV) rm -rf dist
	$(VENV) hatch build

check_docs:
	$(VENV) interrogate openmock --verbose
	$(VENV) pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

make_docs:
	pdoc openmock --html -o docs --force

check_md:
	$(VENV) mdformat README.md docs/*.md
	# $(VENV) linkcheckMarkdown README.md # it is attempting to validate ssl certs
	$(VENV) markdownlint README.md --config .markdownlintrc

check_spelling:
	$(VENV) pylint openmock --enable C0402 --rcfile=.pylintrc_spell
	$(VENV) codespell README.md --ignore-words=private_dictionary.txt
	$(VENV) codespell openmock --ignore-words=private_dictionary.txt

check_changelog:
	$(VENV) changelogmanager validate

.PHONY: gha-validate
gha-validate:
	@echo "Validating GitHub Actions workflows"
	$(VENV) python -c "import pathlib, yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('.github/workflows').glob('*.yml')]; print('YAML parse OK')"
	$(VENV) python -c "from pathlib import Path; import yaml; data=yaml.safe_load(Path('.github/workflows/publish_to_pypi.yml').read_text(encoding='utf-8')); build_steps=data['jobs']['build']['steps']; publish_steps=data['jobs']['pypi-publish']['steps']; up=next(s for s in build_steps if s.get('uses','').startswith('actions/upload-artifact@')); down=next(s for s in publish_steps if s.get('uses','').startswith('actions/download-artifact@')); assert up['with']['name']==down['with']['name']=='packages'; assert up['with']['path']==down['with']['path']=='dist/'; print('Artifact handoff OK:', up['uses'], '->', down['uses'])"
	uvx zizmor --no-progress --no-exit-codes .

.PHONY: gha-pin
gha-pin:
	@echo "Pinning GitHub Actions to current SHAs"
	$(VENV) python -c "import os, subprocess, sys; token=os.environ.get('GITHUB_TOKEN') or subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip(); assert token, 'Set GITHUB_TOKEN or log in with gh auth login'; env=dict(os.environ, GITHUB_TOKEN=token); raise SystemExit(subprocess.run(['gha-update'], env=env).returncode)"

.PHONY: gha-upgrade
gha-upgrade: gha-pin gha-validate
	@echo "GitHub Actions upgrade complete"
