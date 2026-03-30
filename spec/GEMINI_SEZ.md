# Gemini's Vision for Openmock Extensions

The "Management Console" (Streamlit dashboard) revealed several areas where `openmock` can be extended to better serve as a "real" test surrogate.

## 1. Unified Behavior System
Currently, `server_failure` is a standalone decorator. We should move towards a unified `BehaviorManager` that can handle multiple conditions:
- **Latent Response:** Simulate network delays.
- **Partial Success:** Some shards fail, others succeed.
- **Dynamic Cluster State:** Change cluster health based on internal mock state.

## 2. Advanced Administrative APIs
To make dashboards more realistic, we should implement a subset of:
- `_cat` APIs: `_cat/indices`, `_cat/health`, `_cat/nodes`.
- `_nodes` APIs: Returning fake node information.
- `_tasks` APIs: Simulating background tasks.

## 3. Persistent Mock State
Currently, the mock is purely in-memory. For longer-running manual testing or "REST bridge" scenarios, adding an optional file-backed persistence layer (e.g., SQLite or JSON) would be valuable.

## 4. Enhanced Aggregations
The dashboard highlights the need for robust aggregations. We should prioritize:
- `date_histogram` for time-series visualization.
- `stats`, `min`, `max`, `avg` for numeric metrics.
- `nested` aggregations for complex data structures.

## 5. Security Mocking
Support for basic auth headers and simulated permission errors would allow testing security-aware applications.

## 6. Async Consistency
Ensure all sub-clients (`indices`, `cluster`) have full async counterparts that correctly mirror their sync behavior, including decorators.

---

### Implementation Strategy for Dashboard Support

We should focus on making the "internal" state more accessible via public, documented APIs instead of forcing the GUI to use mangled private attributes like `_FakeIndicesClient__documents_dict`. A proper `es.openmock.get_state()` would be a much cleaner interface.
