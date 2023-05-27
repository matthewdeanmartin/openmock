# black openmock && bandit -r openmock && pylint openmock && pre-commit run --all-files
# Get changed files

FILES := $(wildcard **/*.py)

# if you wrap everything in pipenv run, it runs slower.
ifeq ($(origin VIRTUAL_ENV),undefined)
    VENV := pipenv run
else
    VENV :=
endif

Pipfile.lock: Pipfile
	@echo "Installing dependencies"
	@pipenv install --dev

clean-pyc:
	@echo "Skipping clean, too slow"
#	@echo "Removing compiled files"
#	@find . -name '*.pyc' -exec rm -f {} + || true
#	@find . -name '*.pyo' -exec rm -f {} + || true
#	@find . -name '__pycache__' -exec rm -fr {} + || true

clean-test:
	@echo "Removing coverage data"
	@rm -f .coverage || true
	@rm -f .coverage.* || true

clean: clean-pyc clean-test

# tests can't be expected to pass if dependencies aren't installed.
# tests are often slow and linting is fast, so run tests on linted code.
test: clean .build_history/pylint .build_history/bandit Pipfile.lock
	@echo "Running unit tests"
	$(VENV) py.test tests --cov=openmock --cov-report=html --cov-fail-under 90

.build_history:
	@mkdir -p .build_history



.build_history/black: .build_history $(FILES)
	@echo "Formatting code"
	$(VENV) black .
	@touch .build_history/black

.PHONY: black
black: .build_history/black

.build_history/pre-commit: .build_history .build_history/black
	@echo "Pre-commit checks"
	$(VENV) pre-commit run --all-files
	@touch .build_history/pre-commit

.PHONY: pre-commit
pre-commit: .build_history/pre-commit

.build_history/bandit: .build_history $(FILES)
	@echo "Security checks"
	$(VENV)  bandit openmock
	@touch .build_history/bandit

.PHONY: bandit
bandit: .build_history/bandit

.PHONY: pylint
.build_history/pylint: .build_history .build_history/black $(FILES)
	@echo "Linting with pylint"
	$(VENV) pylint openmock --fail-under 10
	@touch .build_history/pylint

# for when using -j (jobs, run in parallel)
.NOTPARALLEL: .build_history/black

check: test pylint bandit pre-commit

.PHONY: build
build: check
	rm -rf dist && poetry build

.PHONY: publish
publish_test:
	rm -rf dist && poetry version minor && poetry build && twine upload -r testpypi dist/*

.PHONY: publish
publish: test
	echo "rm -rf dist && poetry version minor && poetry build && twine upload dist/*"
