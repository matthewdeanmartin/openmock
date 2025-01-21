"""
Simulate some range queries
"""

import datetime
import json
from collections import defaultdict
from typing import Any, Optional

import dateutil.parser
import ranges
from opensearchpy import OpenSearch
from opensearchpy.client.utils import query_params
from opensearchpy.exceptions import ConflictError, NotFoundError, RequestError
from opensearchpy.transport import Transport

from openmock.behaviour.server_failure import server_failure
from openmock.fake_cluster import FakeClusterClient
from openmock.fake_indices import FakeIndicesClient
from openmock.normalize_hosts import _normalize_hosts
from openmock.utilities import (
    extract_ignore_as_iterable,
    get_random_id,
    get_random_scroll_id,
)
from openmock.utilities.decorator import for_all_methods

LT_KEYS = {"lt", "lte"}
GT_KEYS = {"gt", "gte"}


def _create_range(field):
    if not any(x in field.keys() for x in LT_KEYS) or not any(
        x in field.keys() for x in GT_KEYS
    ):
        raise ValueError(
            f"Range queries on maps must contain one of {LT_KEYS} and one of {GT_KEYS}"
        )
    interval_notation = ""
    if "gte" in field:
        interval_notation += f"[{field['gte']}"
    elif "gt" in field:
        interval_notation += f"({field['gt']}"

    if "lte" in field:
        interval_notation += f",{field['lte']}]"
    elif "lt" in field:
        interval_notation += f",{field['lt']})"

    return ranges.Range(interval_notation)


def _compare_sign(sign, lhs, rhs):
    """Convert text to symbol and evaluate"""
    if sign == "gte":
        if lhs < rhs:
            return False
    elif sign == "gt":
        if lhs <= rhs:
            return False
    elif sign == "lte":
        if lhs > rhs:
            return False
    elif sign == "lt":
        if lhs >= rhs:
            return False
    else:
        raise ValueError(f"Invalid comparison type {sign}")
    return True


def _compare_point(comparisons, point):
    for sign, value in comparisons.items():
        if isinstance(point, datetime.datetime):
            value = dateutil.parser.isoparse(value)
        if not _compare_sign(sign, point, value):
            return False
    return True


class QueryType:
    BOOL = "BOOL"
    FILTER = "FILTER"
    MATCH = "MATCH"
    MATCH_ALL = "MATCH_ALL"
    TERM = "TERM"
    TERMS = "TERMS"
    MUST = "MUST"
    RANGE = "RANGE"
    SHOULD = "SHOULD"
    MINIMUM_SHOULD_MATCH = "MINIMUM_SHOULD_MATCH"
    MULTI_MATCH = "MULTI_MATCH"
    MUST_NOT = "MUST_NOT"
    EXISTS = "EXISTS"

    @staticmethod
    def get_query_type(type_str):
        if type_str == "bool":
            return QueryType.BOOL
        if type_str == "filter":
            return QueryType.FILTER
        if type_str == "match":
            return QueryType.MATCH
        if type_str == "match_all":
            return QueryType.MATCH_ALL
        if type_str == "term":
            return QueryType.TERM
        if type_str == "terms":
            return QueryType.TERMS
        if type_str == "must":
            return QueryType.MUST
        if type_str == "range":
            return QueryType.RANGE
        if type_str == "should":
            return QueryType.SHOULD
        if type_str == "minimum_should_match":
            return QueryType.MINIMUM_SHOULD_MATCH
        if type_str == "multi_match":
            return QueryType.MULTI_MATCH
        if type_str == "must_not":
            return QueryType.MUST_NOT
        if type_str == "exists":
            return QueryType.EXISTS

        raise NotImplementedError(f"type {type_str} is not implemented for QueryType")


class MetricType:
    CARDINALITY = "CARDINALITY"

    @staticmethod
    def get_metric_type(type_str):
        if type_str == "cardinality":
            return MetricType.CARDINALITY

        raise NotImplementedError(f"type {type_str} is not implemented for MetricType")


class FakeQueryCondition:
    type = None
    condition = None

    def __init__(self, type, condition):
        self.type = type
        self.condition = condition

    def evaluate(self, document):
        return self._evaluate_for_query_type(document)

    def _evaluate_for_query_type(self, document):
        if self.type == QueryType.MATCH:
            return self._evaluate_for_match_query_type(document)
        if self.type == QueryType.MATCH_ALL:
            return True
        if self.type == QueryType.TERM:
            return self._evaluate_for_term_query_type(document)
        if self.type == QueryType.TERMS:
            return self._evaluate_for_terms_query_type(document)
        if self.type == QueryType.RANGE:
            return self._evaluate_for_range_query_type(document)
        if self.type == QueryType.BOOL:
            return self._evaluate_for_compound_query_type(document)
        if self.type == QueryType.FILTER:
            return self._evaluate_for_compound_query_type(document)
        if self.type == QueryType.MUST:
            return self._evaluate_for_compound_query_type(document)
        if self.type == QueryType.SHOULD:
            return self._evaluate_for_should_query_type(document)
        if self.type == QueryType.MULTI_MATCH:
            return self._evaluate_for_multi_match_query_type(document)
        if self.type == QueryType.MUST_NOT:
            return self._evaluate_for_must_not_query_type(document)
        if self.type == QueryType.EXISTS:
            return self._evaluate_for_exists_query_type(document)
        if self.type == QueryType.MINIMUM_SHOULD_MATCH:
            return self._evaluate_for_compound_query_type(document)
        raise NotImplementedError(
            f"Fake query evaluation not implemented for query type: {self.type}"
        )

    def _evaluate_for_match_query_type(self, document):
        return self._evaluate_for_field(document, True)

    def _evaluate_for_term_query_type(self, document):
        return self._evaluate_for_field(document, False)

    def _evaluate_for_terms_query_type(self, document):
        for field in self.condition:
            for term in self.condition[field]:
                if FakeQueryCondition(QueryType.TERM, {field: term}).evaluate(document):
                    return True
        return False

    def _evaluate_for_field(self, document, ignore_case):
        doc_source = document["_source"]
        return_val = False
        for field, value in self.condition.items():
            return_val = self._compare_value_for_field(
                doc_source, field, value, ignore_case
            )
            if return_val:
                break
        return return_val

    def _evaluate_for_fields(self, document):
        doc_source = document["_source"]
        return_val = False
        value = self.condition.get("query")
        if not value:
            return return_val
        fields = self.condition.get("fields", [])
        for field in fields:
            return_val = self._compare_value_for_field(doc_source, field, value, True)
            if return_val:
                break

        return return_val

    def _evaluate_for_range_query_type(self, document):
        for field, comparisons in self.condition.items():
            doc_val = document["_source"]
            for k in field.split("."):
                if hasattr(doc_val, k):
                    doc_val = getattr(doc_val, k)
                elif k in doc_val:
                    doc_val = doc_val[k]
                else:
                    return False

            if isinstance(doc_val, list):
                return False

            lt_keys = {"lt", "lte"}
            gt_keys = {"gt", "gte"}
            if isinstance(doc_val, dict):
                if not any(x in doc_val.keys() for x in lt_keys) or not any(
                    x in doc_val.keys() for x in gt_keys
                ):
                    raise ValueError(
                        f"Range queries on maps must contain one of {lt_keys} and one of {gt_keys}"
                    )
                document_range = _create_range(doc_val)
                query_range = _create_range(comparisons)
                relation = comparisons.get("relation", "intersects")

                if relation == "within":
                    return document_range in query_range
                if relation == "contains":
                    return query_range in document_range
                return document_range.intersection(query_range) is not None

            return _compare_point(comparisons, doc_val)

    def _evaluate_for_compound_query_type(self, document):
        return_val = False
        if isinstance(self.condition, dict):
            for query_type, sub_query in self.condition.items():
                return_val = FakeQueryCondition(
                    QueryType.get_query_type(query_type), sub_query
                ).evaluate(document)
                if not return_val:
                    return False
        elif isinstance(self.condition, list):
            for sub_condition in self.condition:
                for sub_condition_key in sub_condition:
                    return_val = FakeQueryCondition(
                        QueryType.get_query_type(sub_condition_key),
                        sub_condition[sub_condition_key],
                    ).evaluate(document)
                    if not return_val:
                        return False

        return return_val

    def _evaluate_for_must_not_query_type(self, document):
        if isinstance(self.condition, dict):
            for query_type, sub_query in self.condition.items():
                return_val = FakeQueryCondition(
                    QueryType.get_query_type(query_type), sub_query
                ).evaluate(document)
                if return_val:
                    return False
        elif isinstance(self.condition, list):
            for sub_condition in self.condition:
                for sub_condition_key in sub_condition:
                    return_val = FakeQueryCondition(
                        QueryType.get_query_type(sub_condition_key),
                        sub_condition[sub_condition_key],
                    ).evaluate(document)
                    if return_val:
                        return False
        return True

    def _evaluate_for_should_query_type(self, document):
        return_val = False
        for sub_condition in self.condition:
            for sub_condition_key in sub_condition:
                return_val = FakeQueryCondition(
                    QueryType.get_query_type(sub_condition_key),
                    sub_condition[sub_condition_key],
                ).evaluate(document)
                if return_val:
                    return True
        return return_val

    def _evaluate_for_multi_match_query_type(self, document):
        return self._evaluate_for_fields(document)

    def _evaluate_for_exists_query_type(self, document):
        doc_source = document["_source"]
        field = self.condition.get("field")
        return not self._compare_value_for_field(doc_source, field, None, False)

    def _compare_value_for_field(self, doc_source, field, value, ignore_case):
        if ignore_case and isinstance(value, str):
            value = value.lower()

        doc_val = doc_source
        # Remove boosting
        field, *_ = field.split("*")
        # Remove ".keyword"
        exact_search = field.lower().endswith(".keyword")
        field = field[: -len(".keyword")] if exact_search else field
        for k in field.split("."):
            if hasattr(doc_val, k):
                doc_val = getattr(doc_val, k)
            elif k in doc_val:
                doc_val = doc_val[k]
            else:
                return False

        if not isinstance(doc_val, list):
            doc_val = [doc_val]

        for val in doc_val:
            if not isinstance(val, (int, float, complex)) or val is None:
                val = str(val)
                if ignore_case:
                    val = val.lower()

            if value == val:
                return True
            if isinstance(val, str) and str(value) in val and not exact_search:
                return True

        return False


@for_all_methods([server_failure])
class FakeOpenSearch(OpenSearch):
    # __documents_dict = None

    # pylint: disable=super-init-not-called
    def __init__(self, hosts=None, transport_class=None, **kwargs):
        # self.__documents_dict = {}
        self._FakeIndicesClient__documents_dict = {}
        self.__scrolls = {}
        self.transport = Transport(_normalize_hosts(hosts), **kwargs)

        # This blows up if I call the real base.
        # super(FakeOpenSearch, self).__init__()

    @property
    def __documents_dict(self):
        return self._FakeIndicesClient__documents_dict

    @property
    def indices(self):
        return FakeIndicesClient(self)

    @property
    def cluster(self):
        return FakeClusterClient(self)

    @query_params()
    def ping(self, params=None, headers=None):
        return True

    @query_params()
    def info(self, params=None, headers=None):
        return {
            "status": 200,
            "cluster_name": "openmock",
            "version": {
                "lucene_version": "4.10.4",
                "build_hash": "00f95f4ffca6de89d68b7ccaf80d148f1f70e4d4",
                "number": "1.7.5",
                "build_timestamp": "2016-02-02T09:55:30Z",
                "build_snapshot": False,
            },
            "name": "Nightwatch",
            "tagline": "You Know, for Search",
        }

    @query_params(
        "consistency",
        "op_type",
        "parent",
        "refresh",
        "replication",
        "routing",
        "timeout",
        "timestamp",
        "ttl",
        "version",
        "version_type",
    )
    # def create(self, index, body, doc_type="_doc", id=None, params=None, headers=None):
    def create(  # pylint: disable=too-many-positional-arguments
        self,
        index: Any,
        id: Any,
        body: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        doc_type = "_doc"
        if self.exists(index, id, doc_type=doc_type, params=params):
            raise ConflictError(
                409,
                "action_request_validation_exception",
                "Validation Failed: 1: no documents to get;",
            )

        if index not in self.__documents_dict:
            self.__documents_dict[index] = []

        if id is None:
            id = get_random_id()

        self.__documents_dict[index].append(
            {
                "_type": doc_type,
                "_id": id,
                "_source": body,
                "_index": index,
                "_version": 1,
            }
        )

        return {
            "_type": doc_type,
            "_id": id,
            "created": True,
            "_version": 1,
            "_index": index,
            "result": "created",
        }

    @query_params(
        "consistency",
        "op_type",
        "parent",
        "refresh",
        "replication",
        "routing",
        "timeout",
        "timestamp",
        "ttl",
        "version",
        "version_type",
    )
    # def index(self, index, body, doc_type="_doc", id=None, params=None, headers=None):
    def index(  # pylint: disable=too-many-positional-arguments
        self,
        index: Any,
        body: Any,
        id: Any = None,
        params: Any = None,
        headers: Any = None,
        **kwargs,
    ) -> Any:
        doc_type = "_doc"
        if index not in self.__documents_dict:
            self.__documents_dict[index] = []

        version = 1

        result = "created"
        if id is None:
            id = get_random_id()

        elif self.exists(index, id, doc_type=doc_type, params=params):
            doc = self.get(index, id, doc_type=doc_type, params=params)
            version = doc["_version"] + 1
            self.delete(index, id, doc_type=doc_type)
            result = "updated"

        self.__documents_dict[index].append(
            {
                "_type": doc_type,
                "_id": id,
                "_source": body,
                "_index": index,
                "_version": version,
            }
        )

        return {
            "_type": doc_type,
            "_id": id,
            "created": True,
            "_version": version,
            "_index": index,
            "result": result,
        }

    @query_params(
        "consistency",
        "op_type",
        "parent",
        "refresh",
        "replication",
        "routing",
        "timeout",
        "timestamp",
        "ttl",
        "version",
        "version_type",
    )
    # def bulk(self, body, index=None, doc_type=None, params=None, headers=None):
    def bulk(
        self,
        body: Any,
        index: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        doc_type = None
        items = []
        errors = False

        for raw_line in body.splitlines():
            if len(raw_line.strip()) > 0:
                line = json.loads(raw_line)

                if any(
                    action in line for action in ["index", "create", "update", "delete"]
                ):
                    action = next(iter(line.keys()))

                    version = 1
                    index = line[action].get("_index") or index
                    doc_type = line[action].get(
                        "_type", "_doc"
                    )  # _type is deprecated in 7.x

                    if action in ["delete", "update"] and not line[action].get("_id"):
                        raise RequestError(
                            400, "action_request_validation_exception", "missing id"
                        )

                    document_id = line[action].get("_id", get_random_id())

                    if action == "delete":
                        status, result, error = self._validate_action(
                            action, index, document_id, doc_type, params=params
                        )
                        item = {
                            action: {
                                "_type": doc_type,
                                "_id": document_id,
                                "_index": index,
                                "_version": version,
                                "status": status,
                            }
                        }
                        if error:
                            errors = True
                            item[action]["error"] = result
                        else:
                            self.delete(
                                index, document_id, doc_type=doc_type, params=params
                            )
                            item[action]["result"] = result
                        items.append(item)

                    if index not in self.__documents_dict:
                        self.__documents_dict[index] = []
                else:
                    if "doc" in line and action == "update":
                        source = line["doc"]
                    else:
                        source = line
                    status, result, error = self._validate_action(
                        action, index, document_id, doc_type, params=params
                    )
                    item = {
                        action: {
                            "_type": doc_type,
                            "_id": document_id,
                            "_index": index,
                            "_version": version,
                            "status": status,
                        }
                    }
                    if not error:
                        item[action]["result"] = result
                        if self.exists(
                            index, document_id, doc_type=doc_type, params=params
                        ):
                            doc = self.get(
                                index, document_id, doc_type=doc_type, params=params
                            )
                            version = doc["_version"] + 1
                            self.delete(
                                index, document_id, doc_type=doc_type, params=params
                            )

                        self.__documents_dict[index].append(
                            {
                                "_type": doc_type,
                                "_id": document_id,
                                "_source": source,
                                "_index": index,
                                "_version": version,
                            }
                        )
                    else:
                        errors = True
                        item[action]["error"] = result
                    items.append(item)
        return {"errors": errors, "items": items}

    def _validate_action(
        self, action, index, document_id, doc_type, params=None
    ):  # pylint: disable=too-many-positional-arguments
        if action in ["index", "update"] and self.exists(
            index, id=document_id, doc_type=doc_type, params=params
        ):
            return 200, "updated", False
        if action == "create" and self.exists(
            index, id=document_id, doc_type=doc_type, params=params
        ):
            return 409, "version_conflict_engine_exception", True
        if action in ["index", "create"] and not self.exists(
            index, id=document_id, doc_type=doc_type, params=params
        ):
            return 201, "created", False
        if action == "delete" and self.exists(
            index, id=document_id, doc_type=doc_type, params=params
        ):
            return 200, "deleted", False
        if action == "update" and not self.exists(
            index, id=document_id, doc_type=doc_type, params=params
        ):
            return 404, "document_missing_exception", True
        if action == "delete" and not self.exists(
            index, id=document_id, doc_type=doc_type, params=params
        ):
            return 404, "not_found", True
        raise NotImplementedError(f"{action} behaviour hasn't been implemented")

    @query_params("parent", "preference", "realtime", "refresh", "routing")
    # def exists(self, index, id, doc_type=None, params=None, headers=None):
    def exists(
        self,
        index: Any,
        id: Any,
        params: Any = None,
        headers: Any = None,
        **kwargs,
    ) -> Any:
        doc_type = None
        result = False
        if index in self.__documents_dict:
            for document in self.__documents_dict[index]:
                if document.get("_id") == id and (
                    document.get("_type") == doc_type or doc_type is None
                ):
                    result = True
                    break
        return result

    @query_params(
        "_source",
        "_source_exclude",
        "_source_include",
        "fields",
        "parent",
        "preference",
        "realtime",
        "refresh",
        "routing",
        "version",
        "version_type",
    )
    # def get(self, index, id, doc_type="_all", params=None, headers=None):
    def get(
        self, index: Any, id: Any, params: Any = None, headers: Any = None, **kwargs
    ) -> Any:
        doc_type = "_all"
        ignore = extract_ignore_as_iterable(params)
        result = None

        if index in self.__documents_dict:
            for document in self.__documents_dict[index]:
                if document.get("_id") == id:
                    if doc_type == "_all":
                        result = document
                        break
                    if document.get("_type") == doc_type:
                        result = document
                        break

        if result:
            result["found"] = True
            return result
        if params and 404 in ignore:
            return {"found": False}
        error_data = {"_index": index, "_type": doc_type, "_id": id, "found": False}
        raise NotFoundError(404, json.dumps(error_data))

    @query_params(
        "_source",
        "_source_excludes",
        "_source_includes",
        "if_primary_term",
        "if_seq_no",
        "lang",
        "refresh",
        "require_alias",
        "retry_on_conflict",
        "routing",
        "timeout",
        "wait_for_active_shards",
    )
    def update(
        self, index, id, body, params=None, headers=None
    ):  # pylint: disable=too-many-positional-arguments
        if not body:
            raise RequestError(
                400,
                "action_request_validation_exception",
                "Validation Failed: 1: script or doc is missing;",
            )
        if "doc" not in body and "script" not in body:
            field = list(body.keys())
            raise RequestError(
                400,
                "x_content_parse_exception",
                f"[1:2] [UpdateRequest] unknown field [{field[0]}]",
            )
        if "doc" in body and "script" in body:
            raise RequestError(
                400,
                "action_request_validation_exception",
                "Validation Failed: 1: can't provide both script and doc;",
            )

        result = None

        if index in self.__documents_dict:
            for document in self.__documents_dict[index]:
                if document.get("_id") == id:
                    if "doc" in body:
                        document["_source"] = {**document["_source"], **body["doc"]}
                        document["_version"] += 1

                        # TODO: Might be removed since it seems that latest open search doesn't respond the _type anymore.
                        result = {
                            "_index": index,
                            "_id": id,
                            "_type": document.get("_type", "_doc"),
                            "_version": document["_version"],
                            "result": "updated",
                            "_shards": {"total": 1, "successful": 1, "failed": 0},
                        }
                    elif "script" in body:
                        # TODO: Add pain(ful)less language support
                        raise NotImplementedError(
                            "Using script is currently not supported."
                        )

        if result:
            return result
        raise NotFoundError(
            404, "document_missing_exception", f"[{id}]: document missing"
        )

    @query_params(
        "_source",
        "_source_excludes",
        "_source_includes",
        "allow_no_indices",
        "analyze_wildcard",
        "analyzer",
        "conflicts",
        "default_operator",
        "df",
        "expand_wildcards",
        "from_",
        "ignore_unavailable",
        "lenient",
        "max_docs",
        "pipeline",
        "preference",
        "q",
        "refresh",
        "request_cache",
        "requests_per_second",
        "routing",
        "scroll",
        "scroll_size",
        "search_timeout",
        "search_type",
        "size",
        "slices",
        "sort",
        "stats",
        "terminate_after",
        "timeout",
        "version",
        "version_type",
        "wait_for_active_shards",
        "wait_for_completion",
    )
    def update_by_query(
        self,
        index: Any,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        # def update_by_query(
        #     self, index, body=None, doc_type=None, params=None, headers=None
        # ):
        doc_type = None
        # Actually it only supports script equal operations
        # TODO: Full support from painless language
        total_updated = 0
        if isinstance(index, list):
            (index,) = index
        new_values = {}
        script_params = body["script"]["params"]
        script_source = body["script"]["source"].replace("ctx._source.", "").split(";")
        for sentence in script_source:
            if sentence:
                field, _, value = sentence.split()
                if value.startswith("params."):
                    _, key = value.split(".")
                    value = script_params.get(key)
                new_values[field] = value

        matches = self.search(
            index=index, doc_type=doc_type, body=body, params=params, headers=headers
        )
        if matches["hits"]["total"]:
            for hit in matches["hits"]["hits"]:
                body = hit["_source"]
                body.update(new_values)
                self.index(index, body, doc_type=hit["_type"], id=hit["_id"])
                total_updated += 1

        return {
            "took": 1,
            "time_out": False,
            "total": matches["hits"]["total"],
            "updated": total_updated,
            "deleted": 0,
            "batches": 1,
            "version_conflicts": 0,
            "noops": 0,
            "retries": 0,
            "throttled_millis": 100,
            "requests_per_second": 100,
            "throttled_until_millis": 0,
            "failures": [],
        }

    @query_params(
        "_source",
        "_source_exclude",
        "_source_include",
        "preference",
        "realtime",
        "refresh",
        "routing",
        "stored_fields",
    )
    def mget(
        self,
        body: Any,
        index: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        # def mget(self, body, index, doc_type="_all", params=None, headers=None):
        doc_type = "_all"
        docs = body.get("docs")
        ids = [doc["_id"] for doc in docs]
        results = []
        for id in ids:
            # pylint: disable=bare-except
            try:
                results.append(
                    self.get(
                        index, id, doc_type=doc_type, params=params, headers=headers
                    )
                )
            except:  # noqa
                pass  # nosec
        if not results:
            raise RequestError(
                400,
                "action_request_validation_exception",
                "Validation Failed: 1: no documents to get;",
            )
        return {"docs": results}

    @query_params(
        "_source",
        "_source_exclude",
        "_source_include",
        "parent",
        "preference",
        "realtime",
        "refresh",
        "routing",
        "version",
        "version_type",
    )
    # def get_source(self, index, doc_type, id, params=None, headers=None):
    def get_source(
        self,
        index: Any,
        id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        doc_type = None
        document = self.get(index=index, doc_type=doc_type, id=id, params=params)
        return document.get("_source")

    @query_params(
        "_source",
        "_source_exclude",
        "_source_include",
        "allow_no_indices",
        "analyze_wildcard",
        "analyzer",
        "default_operator",
        "df",
        "expand_wildcards",
        "explain",
        "fielddata_fields",
        "fields",
        "from_",
        "ignore_unavailable",
        "lenient",
        "lowercase_expanded_terms",
        "min_score",
        "preference",
        "q",
        "request_cache",
        "routing",
        "scroll",
        "search_type",
        "size",
        "sort",
        "stats",
        "suggest_field",
        "suggest_mode",
        "suggest_size",
        "suggest_text",
        "terminate_after",
        "timeout",
        "track_scores",
        "version",
    )
    # def count(self, index=None, doc_type=None, body=None, params=None, headers=None):
    def count(
        self,
        body: Any = None,
        index: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        doc_type = None
        searchable_indexes = self._normalize_index_to_list(index)

        i = 0
        for searchable_index in searchable_indexes:
            for document in self.__documents_dict[searchable_index]:
                if doc_type and document.get("_type") != doc_type:
                    continue
                i += 1
        result = {
            "count": i,
            "_shards": {"successful": 1, "skipped": 0, "failed": 0, "total": 1},
        }

        return result

    def _get_fake_query_condition(self, query_type_str, condition):
        return FakeQueryCondition(QueryType.get_query_type(query_type_str), condition)

    @query_params(
        "ccs_minimize_roundtrips",
        "max_concurrent_searches",
        "max_concurrent_shard_requests",
        "pre_filter_shard_size",
        "rest_total_hits_as_int",
        "search_type",
        "typed_keys",
    )
    # def msearch(self, body, index=None, doc_type=None, params=None, headers=None):
    def msearch(
        self,
        body: Any,
        index: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        def grouped(iterable):
            if len(iterable) % 2 != 0:
                # pylint: disable=broad-exception-raised
                raise Exception("Malformed body")
            iterator = iter(iterable)
            while True:
                try:
                    yield (next(iterator)["index"], next(iterator))
                except StopIteration:
                    break

        responses = []
        took = 0
        for ind, query in grouped(body):
            response = self.search(index=ind, body=query)
            took += response["took"]
            responses.append(response)
        result = {"took": took, "responses": responses}
        return result

    @query_params(
        "_source",
        "_source_exclude",
        "_source_include",
        "allow_no_indices",
        "analyze_wildcard",
        "analyzer",
        "default_operator",
        "df",
        "expand_wildcards",
        "explain",
        "fielddata_fields",
        "fields",
        "from_",
        "ignore_unavailable",
        "lenient",
        "lowercase_expanded_terms",
        "preference",
        "q",
        "request_cache",
        "routing",
        "scroll",
        "search_type",
        "size",
        "sort",
        "stats",
        "suggest_field",
        "suggest_mode",
        "suggest_size",
        "suggest_text",
        "terminate_after",
        "timeout",
        "track_scores",
        "version",
    )
    def search(
        self,
        body: Any = None,
        index: Any = None,
        params: Any = None,
        headers: Any = None,
        **kwargs,
    ) -> Any:
        # def search(self, index=None, doc_type=None, body=None, params=None, headers=None):
        doc_type: Optional[list] = None
        searchable_indexes = self._normalize_index_to_list(index)

        matches = []
        conditions = []

        if body and "query" in body:
            query = body["query"]
            for query_type_str, condition in query.items():
                conditions.append(
                    self._get_fake_query_condition(query_type_str, condition)
                )
        for searchable_index in searchable_indexes:
            for document in self.__documents_dict[searchable_index]:
                if doc_type:
                    # pylint: disable=unsupported-membership-test
                    if (
                        isinstance(doc_type, list)
                        and document.get("_type") not in doc_type
                    ):
                        continue
                    if isinstance(doc_type, str) and document.get("_type") != doc_type:
                        continue
                if conditions:
                    for condition in conditions:
                        if condition.evaluate(document):
                            matches.append(document)
                            break
                else:
                    matches.append(document)

        for match in matches:
            self._find_and_convert_data_types(match["_source"])

        result = {
            "hits": {
                "total": {"value": len(matches), "relation": "eq"},
                "max_score": 1.0,
            },
            "_shards": {
                # Simulate indexes with 1 shard each
                "successful": len(searchable_indexes),
                "skipped": 0,
                "failed": 0,
                "total": len(searchable_indexes),
            },
            "took": 1,
            "timed_out": False,
        }

        hits = []
        for match in matches:
            match["_score"] = 1.0
            hits.append(match)

        # build aggregations
        if body is not None and "aggs" in body:
            aggregations = {}

            for aggregation, definition in body["aggs"].items():
                aggregations[aggregation] = {
                    "doc_count_error_upper_bound": 0,
                    "sum_other_doc_count": 0,
                    "buckets": self.make_aggregation_buckets(definition, matches),
                }

            if aggregations:
                result["aggregations"] = aggregations

        if "scroll" in params:
            result["_scroll_id"] = str(get_random_scroll_id())
            params["size"] = int(params.get("size", 10))
            params["from"] = int(
                params.get("from") + params.get("size") if "from" in params else 0
            )
            self.__scrolls[result.get("_scroll_id")] = {
                "index": index,
                "doc_type": doc_type,
                "body": body,
                "params": params,
            }
            hits = hits[params.get("from") : params.get("from") + params.get("size")]
        elif "size" in params:
            hits = hits[: int(params["size"])]
        elif body and "size" in body:
            hits = hits[: int(body["size"])]

        result["hits"]["hits"] = hits

        return result

    @query_params("scroll")
    # def scroll(self, scroll_id, params=None, headers=None):
    def scroll(
        self,
        body: Any = None,
        scroll_id: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        scroll = self.__scrolls.pop(scroll_id)
        result = self.search(
            index=scroll.get("index"),
            doc_type=scroll.get("doc_type"),
            body=scroll.get("body"),
            params=scroll.get("params"),
        )
        return result

    @query_params(
        "consistency",
        "parent",
        "refresh",
        "replication",
        "routing",
        "timeout",
        "version",
        "version_type",
    )
    # def delete(self, index, id, doc_type=None, params=None, headers=None):
    def delete(
        self, index: Any, id: Any, params: Any = None, headers: Any = None, **kwargs
    ) -> Any:
        doc_type = None
        found = False
        ignore = extract_ignore_as_iterable(params)

        if index in self.__documents_dict:
            for document in self.__documents_dict[index]:
                if document.get("_id") == id:
                    found = True
                    if doc_type and document.get("_type") != doc_type:
                        found = False
                    if found:
                        self.__documents_dict[index].remove(document)
                        break

        result_dict = {
            "found": found,
            "_index": index,
            "_type": doc_type,
            "_id": id,
            "_version": 1,
        }

        if found:
            return result_dict
        if params and 404 in ignore:
            return {"found": False}
        raise NotFoundError(404, json.dumps(result_dict))

    @query_params(
        "allow_no_indices",
        "expand_wildcards",
        "ignore_unavailable",
        "preference",
        "routing",
    )
    def suggest(self, body, index=None, params=None, headers=None):
        if index is not None and index not in self.__documents_dict:
            raise NotFoundError(404, f"IndexMissingException[[{index}] missing]")

        result_dict = {}
        for key, value in body.items():
            text = value.get("text")
            suggestion = (
                int(text) + 1 if isinstance(text, int) else f"{text}_suggestion"
            )
            result_dict[key] = [
                {
                    "text": text,
                    "length": 1,
                    "options": [{"text": suggestion, "freq": 1, "score": 1.0}],
                    "offset": 0,
                }
            ]
        return result_dict

    def _normalize_index_to_list(self, index):
        # Ensure to have a list of index
        if index is None:
            searchable_indexes = self.__documents_dict.keys()
        elif isinstance(index, str):
            searchable_indexes = [index]
        elif isinstance(index, list):
            searchable_indexes = index
        else:
            # Is it the correct exception to use ?
            raise ValueError("Invalid param 'index'")

        # Check index(es) exists
        for searchable_index in searchable_indexes:
            if searchable_index not in self.__documents_dict:
                raise NotFoundError(
                    404, f"IndexMissingException[[{searchable_index}] missing]"
                )

        return searchable_indexes

    @classmethod
    def _find_and_convert_data_types(cls, document):
        for key, value in document.items():
            if isinstance(value, dict):
                cls._find_and_convert_data_types(value)
            elif isinstance(value, datetime.datetime):
                document[key] = value.isoformat()

    def make_aggregation_buckets(self, aggregation, documents):
        if "composite" in aggregation:
            return self.make_composite_aggregation_buckets(aggregation, documents)
        return []

    def make_composite_aggregation_buckets(self, aggregation, documents):
        def make_key(doc_source, agg_source):
            attr = list(agg_source.values())[0]["terms"]["field"]
            return doc_source[attr]

        def make_bucket(bucket_key, bucket):
            out = {
                "key": dict(zip(bucket_key_fields, bucket_key)),
                "doc_count": len(bucket),
            }

            for metric_key, metric_definition in aggregation["aggs"].items():
                metric_type_str = list(metric_definition)[0]
                metric_type = MetricType.get_metric_type(metric_type_str)
                attr = metric_definition[metric_type_str]["field"]
                data = [doc[attr] for doc in bucket]

                if metric_type == MetricType.CARDINALITY:
                    value = len(set(data))
                else:
                    raise NotImplementedError(
                        f"Metric type '{metric_type}' not implemented"
                    )

                out[metric_key] = {"value": value}
            return out

        agg_sources = aggregation["composite"]["sources"]
        buckets = defaultdict(list)
        bucket_key_fields = [list(src)[0] for src in agg_sources]
        for document in documents:
            doc_src = document["_source"]
            key = tuple(
                make_key(doc_src, agg_src)
                for agg_src in aggregation["composite"]["sources"]
            )
            buckets[key].append(doc_src)

        buckets = sorted(((k, v) for k, v in buckets.items()), key=lambda x: x[0])
        buckets = [make_bucket(bucket_key, bucket) for bucket_key, bucket in buckets]
        return buckets
