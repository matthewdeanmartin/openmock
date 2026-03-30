# Openmock Analysis & Roadmap

## Current State Analysis

`openmock` is a mature Python-based mock for the `opensearch-py` client. It provides a decorator-based approach to replace real OpenSearch connections with a local, in-memory fake.

### Key Strengths:
- **Comprehensive Client Coverage:** Supports both sync (`OpenSearch`) and async (`AsyncOpenSearch`) clients.
- **Detailed Indices Support:** Implements common index operations like create, delete, exists, and refresh.
- **Rich Query Support:** Includes logic for range queries, term queries, and basic boolean logic.
- **Extensible Behaviors:** Features a behavior system (e.g., `server_failure`) to simulate error conditions.
- **High Compatibility:** Tested against multiple Python versions and OpenSearch client versions.

### Gaps / Opportunities:
- **Missing Aggregations:** Most fakes struggle with complex aggregations; adding basic `terms`, `sum`, `avg` aggregations would be a major win.
- **Limited "Administrative" APIs:** APIs like `_cat`, `_tasks`, or `_cluster/settings` are often minimally implemented or missing.
- **REST Interface:** Currently, it's a library-level mock. A REST server wrapper would allow non-Python applications to use it.
- **Visual Feedback:** No easy way to "see" what's inside the fake during a debug session or manual testing.

---

## Roadmap

### 1. Developer Experience: The `Justfile`
Provide a robust `Justfile` to manage a real OpenSearch instance locally for developers who can't afford cloud costs.

- `install`: Scripted download and setup of OpenSearch (using `uv` where possible or standard shell tools).
- `run`: Start OpenSearch in the background.
- `stop`: Gracefully shut down the local instance.
- `logs`: Tail the OpenSearch logs.
- `clean`: Wipe local data and start fresh.

### 2. Interaction: The Openmock GUI
A "Management Console" for the fake.
- **Framework:** Streamlit (chosen for Python ecosystem compatibility and rapid development).
- **Features:**
    - Index Browser: List all current fake indices.
    - Document Explorer: Search and view documents stored in the fake.
    - Query Sandbox: Paste a JSON query and see how the fake responds.
    - Behavior Toggle: Enable/disable `server_failure` or other future behaviors via UI.

### 3. Capability Expansion: More OpenSearch Behaviors
- **Aggregations:** Implement the `aggs` key in search results for common metric and bucket aggregations.
- **Nested Queries:** Support for `nested` field types and queries.
- **Painless Scripting (Subset):** Minimal support for simple update scripts.
- **Alias Management:** Better support for index aliases.

### 4. Integration: The Mock REST Server
A FastAPI wrapper that:
- Loads `openmock` in the background.
- Exposes standard OpenSearch endpoints (`/_search`, `/{index}/_doc`, etc.).
- Allows `curl` or OpenSearch Dashboards to connect to the fake.

---

## Execution Plan

1. **Phase 1: Tooling (The Justfile)** - Immediate setup of local environment management.
2. **Phase 2: GUI Prototype** - Build a basic Streamlit app to visualize the `openmock` state.
3. **Phase 3: Logic Depth** - Iteratively add support for Aggregations and Nested queries.
4. **Phase 4: The REST bridge** - Wrap the fake in a web server.
