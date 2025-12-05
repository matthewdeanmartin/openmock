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