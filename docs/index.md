# Openmock docs

Openmock is a Python test surrogate for `opensearch-py`. It gives unit tests an in-memory, stateful stand-in for `OpenSearch` and `AsyncOpenSearch` so application code can exercise realistic indexing, search, update, and delete flows without a live cluster.


## What to read

- [Using Openmock in unit tests](unit-testing.md) - how the decorator works, what testing style this is, and practical examples.
- [Web UI, desktop GUI, and REST bridge](web-ui.md) - the Tkinter desktop GUI, the Streamlit management console, and the lightweight HTTP bridge for manual exploration.
- [Contributing](contributing.md) - local setup, validation commands, and a short tour of the code.
- [API reference](openmock/index.html) - generated reference docs for the package.

## What Openmock is

Openmock is best understood as a **stateful fake** or **test surrogate**:

- It is not a pure mock that only asserts calls.
- It is not a full OpenSearch emulator.
- It is a small in-memory implementation of the client API that keeps document state and returns OpenSearch-shaped responses.

That makes it a good fit for unit tests that care about application behavior across several client calls, such as "index a document, search for it, then update it".

## Current scope

The package currently includes:

- sync and async fake clients,
- index and cluster sub-clients,
- a behavior toggle for simulated server failures,
- a Streamlit web UI for inspecting fake state (`openmock` command, requires `openmock[web]`),
- a Tkinter desktop GUI for inspecting fake state (`openmock gui` command, no extra dependencies),
- a FastAPI bridge so HTTP tools can talk to the fake,
- a parity seam used by tests to swap the fake for a real OpenSearch backend.

For the exact supported surface, check the tests under `tests/` and the generated API docs.
