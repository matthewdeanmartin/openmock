"""
Fake Index state
"""

from opensearchpy._async.client.indices import IndicesClient
from opensearchpy.client.utils import query_params


class FakeAsyncIndicesClient(IndicesClient):
    @query_params("master_timeout", "timeout")
    async def create(self, index, body=None, params=None, headers=None):
        """
        Fake index creation
        """
        documents_dict = self.__get_documents_dict()
        if index not in documents_dict:
            documents_dict[index] = []

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

    @query_params("master_timeout", "timeout")
    async def delete(self, index, params=None, headers=None):
        """Fake index deletion"""
        documents_dict = self.__get_documents_dict()
        if index in documents_dict:
            del documents_dict[index]

    @query_params(
        "cluster_manager_timeout",
        "error_trace",
        "filter_path",
        "human",
        "master_timeout",
        "pretty",
        "source",
        "task_execution_timeout",
        "timeout",
        "wait_for_active_shards",
        "wait_for_completion",
    )
    async def clone(
        self,
        index,
        target,
        body=None,
        params=None,
        headers=None,
    ):
        if await self.exists(target):
            msg = "Target already exists"
            raise ValueError(msg)
        if not await self.exists(index):
            msg = "index doesn't exist"
            raise ValueError(msg)
        documents_dict = self.__get_documents_dict()
        documents_dict[target] = documents_dict.pop(index)

    def __get_documents_dict(self):
        """Get the documents dictionary"""
        return self.client.__documents_dict
