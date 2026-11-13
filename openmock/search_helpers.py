"""Shared, deterministic search response handling for both mock clients."""

from typing import Any

from opensearchpy.exceptions import RequestError


def sort_hits(hits: list[dict[str, Any]], sort: Any) -> list[dict[str, Any]]:
    """Sort on multiple source fields, placing missing values last by default."""
    if not sort:
        return hits
    clauses = sort if isinstance(sort, list) else [sort]
    for clause in reversed(clauses):
        if isinstance(clause, str):
            field, _, order = clause.partition(":")
            options = {"order": order or "asc"}
        else:
            field, options = next(iter(clause.items()))
            if isinstance(options, str):
                options = {"order": options}
        present = [hit for hit in hits if hit["_source"].get(field) is not None]
        missing = [hit for hit in hits if hit["_source"].get(field) is None]
        present.sort(
            key=lambda hit: hit["_source"][field],  # pylint: disable=cell-var-from-loop
            reverse=options.get("order", "asc") == "desc",
        )
        hits = (
            missing + present
            if options.get("missing") == "_first"
            else present + missing
        )
    return hits


def pagination(body: Any, params: Any) -> tuple[int, int]:
    """Query parameters override body pagination; searches default to ten hits."""
    body = body or {}
    params = params or {}
    start = int(params.get("from", params.get("from_", body.get("from", 0))))
    size = int(params.get("size", body.get("size", 10)))
    if start < 0 or size < 0:
        raise RequestError(
            400, "illegal_argument_exception", "from and size must be nonnegative"
        )
    return start, size
