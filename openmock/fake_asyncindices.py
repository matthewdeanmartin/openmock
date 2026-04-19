"""
Fake Index state
"""

from opensearchpy._async.client.indices import IndicesClient
from opensearchpy.client.utils import query_params

from openmock.behaviour.server_failure import server_failure
from openmock.utilities.decorator import for_all_methods


@for_all_methods([server_failure])
class FakeAsyncIndicesClient(IndicesClient):
    @query_params("master_timeout", "timeout")
    async def create(self, index, body=None, params=None, headers=None):
        """
        Fake index creation
        """
        documents_dict = self.__get_documents_dict()
        if index not in documents_dict:
            documents_dict[index] = []
        return {"acknowledged": True, "shards_acknowledged": True, "index": index}

    @query_params("allow_no_indices", "expand_wildcards", "ignore_unavailable", "local")
    async def exists(self, index, params=None, headers=None):
        """
        Fake index exists
        """
        return index in self.__get_documents_dict()

    @query_params(
        "allow_no_indices",
        "expand_wildcards",
        "force",
        "ignore_unavailable",
        "operation_threading",
    )
    async def refresh(self, index=None, params=None, headers=None):
        """
        Fake index refresh (no implementation)
        """
        return {"_shards": {"total": 1, "successful": 1, "failed": 0}}

    @query_params("master_timeout", "timeout")
    async def delete(self, index, params=None, headers=None):
        """Fake index deletion"""
        documents_dict = self.__get_documents_dict()
        if index in documents_dict:
            del documents_dict[index]
        return {"acknowledged": True}

    @query_params("master_timeout", "timeout")
    async def put_alias(self, index, name, body=None, params=None, headers=None, **kwargs):
        """Fake put alias"""
        aliases_dict = self.__get_aliases_dict()
        for idx in self._normalize_index_to_list(index):
            if idx not in aliases_dict:
                aliases_dict[idx] = {"aliases": {}}
            aliases_dict[idx]["aliases"][name] = {}
        return {"acknowledged": True}

    @query_params("allow_no_indices", "expand_wildcards", "ignore_unavailable", "local")
    async def get_alias(self, index=None, name=None, params=None, headers=None, **kwargs):
        """Fake get alias"""
        aliases_dict = self.__get_aliases_dict()
        res = {}
        for idx in self._normalize_index_to_list(index):
            if idx in aliases_dict:
                res[idx] = aliases_dict[idx]
            else:
                res[idx] = {"aliases": {}}
        return res

    @query_params("master_timeout", "timeout")
    async def delete_alias(self, index, name, params=None, headers=None, **kwargs):
        """Fake delete alias"""
        aliases_dict = self.__get_aliases_dict()
        for idx in self._normalize_index_to_list(index):
            if idx in aliases_dict and name in aliases_dict[idx]["aliases"]:
                del aliases_dict[idx]["aliases"][name]
        return {"acknowledged": True}

    async def stats(self, index=None, metric=None, params=None, headers=None, **kwargs):
        """Fake stats"""
        return {
            "_shards": {"total": 1, "successful": 1, "failed": 0},
            "indices": {
                idx: {"uuid": "uuid", "primaries": {}, "total": {}}
                for idx in self._normalize_index_to_list(index)
            },
        }

    def __get_aliases_dict(self):
        """Get the aliases dictionary"""
        return self.client.__aliases_dict

    def __get_documents_dict(self):
        """Get the documents dictionary"""
        return self.client.__documents_dict

    def _normalize_index_to_list(self, index):
        """Normalize index to a list of indexes"""
        if index is None or index == "*" or index == "_all":
            return list(self.__get_documents_dict().keys())
        if isinstance(index, str):
            res = [idx.strip() for idx in index.split(",")]
            return res
        if isinstance(index, list):
            return index
        return [index]
