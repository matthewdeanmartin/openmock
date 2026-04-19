# Openmock Project Justfile

OS_VERSION := "3.5.0"
OS_ZIP := "opensearch-" + OS_VERSION + "-windows-x64.zip"
OS_URL := "https://artifacts.opensearch.org/releases/bundle/opensearch/" + OS_VERSION + "/" + OS_ZIP
OS_DIR := ".opensearch"

# --- REAL OPENSEARCH (Port 9200) ---

# Install real OpenSearch 3.5.0 locally
install-real:
	@mkdir -p {{OS_DIR}}
	@if [ ! -f {{OS_DIR}}/{{OS_ZIP}} ]; then \
		echo "Downloading OpenSearch {{OS_VERSION}}..."; \
		curl -L {{OS_URL}} -o {{OS_DIR}}/{{OS_ZIP}}; \
	fi
	@if [ ! -d {{OS_DIR}}/opensearch-{{OS_VERSION}} ]; then \
		echo "Extracting OpenSearch..."; \
		unzip -q {{OS_DIR}}/{{OS_ZIP}} -d {{OS_DIR}}; \
	fi
	@echo "OpenSearch installed in {{OS_DIR}}/opensearch-{{OS_VERSION}}"

# Start real OpenSearch in background
run-real:
	@echo "OpenSearch starting in background on http://localhost:9200..."
	@export OPENSEARCH_INITIAL_ADMIN_PASSWORD='OpenmockPassword123!' && \
	cd {{OS_DIR}}/opensearch-{{OS_VERSION}} && \
	./opensearch-windows-install.bat &

# Stop real OpenSearch
stop-real:
	@echo "Stopping OpenSearch processes..."
	@# On Windows/Git Bash, we look for the java process running from our directory
	@WMIC process where "CommandLine like '%{{OS_DIR}}%'" delete 2>/dev/null || \
	 taskkill /F /IM java.exe /FI "WINDOWTITLE eq OpenSearch*" 2>/dev/null || \
	 echo "No OpenSearch process found or already stopped."

# Check status of real OpenSearch
status-real:
	@if curl -s -I http://localhost:9200 > /dev/null; then \
		echo "Real OpenSearch is RUNNING (Port 9200)"; \
	else \
		echo "Real OpenSearch is STOPPED"; \
	fi

# Start real OpenSearch in Docker for parity testing
run-real-docker:
	uv run python scripts/opensearch_docker.py start

# Stop the Dockerized parity OpenSearch
stop-real-docker:
	uv run python scripts/opensearch_docker.py stop

# Check Dockerized parity OpenSearch status
status-real-docker:
	uv run python scripts/opensearch_docker.py status

# Run tests against Dockerized OpenSearch
test-real:
	uv run python scripts/opensearch_docker.py test tests

# --- MOCK OPENSEARCH (Port 9201) ---

# Start the Openmock Management Console
web:
	uv run openmock

# Start a Mock REST Server (allows curl/dashboards to connect to the fake)
run-mock-server:
	uv run python scripts/rest_bridge.py

# --- DEVELOPER TASKS ---

# Ensure dependencies are installed
sync:
	uv sync --all-extras

# Build the project
build: sync
	uv build

# Run tests
test: sync
	uv run pytest tests
