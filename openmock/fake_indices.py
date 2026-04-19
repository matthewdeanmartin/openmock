"""
Fake Index state
"""

from opensearchpy.client.indices import IndicesClient
from opensearchpy.client.utils import query_params

from openmock.behaviour.server_failure import server_failure
from openmock.utilities.decorator import for_all_methods


@for_all_methods([server_failure])
class FakeIndicesClient(IndicesClient):
    @query_params("master_timeout", "timeout")
    def create(self, index, body=None, params=None, headers=None, **kwargs):
        """
        Fake index creation
        """
        invalid_chars = [" ", '"', "*", "\\", "<", "|", ",", ">", "/", "?"]
        for char in invalid_chars:
            if char in index:
                from opensearchpy.exceptions import RequestError
                raise RequestError(
                    400, 
                    'invalid_index_name_exception', 
                    f"Invalid index name [{index}], must not contain the following characters [ , \", *, \\, <, |, ,, >, /, ?]"
                )

        documents_dict = self.__get_documents_dict()
        if index not in documents_dict:
            documents_dict[index] = []
        
        if body:
            if "mappings" in body:
                mappings_dict = self.__get_mappings_dict()
                mappings_dict[index] = {"mappings": body["mappings"]}
            if "settings" in body:
                settings_dict = self.__get_settings_dict()
                settings = body["settings"]
                # Store them as they are, but ensure we can access them in get_settings
                settings_dict[index] = {"settings": settings}

        return {"acknowledged": True, "shards_acknowledged": True, "index": index}

    @query_params("allow_no_indices", "expand_wildcards", "ignore_unavailable", "local")
    def exists(self, index, params=None, headers=None, **kwargs):
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
    def refresh(self, index=None, params=None, headers=None, **kwargs):
        """
        Fake index refresh (no implementation)
        """
        return {"_shards": {"total": 1, "successful": 1, "failed": 0}}

    @query_params("master_timeout", "timeout")
    def delete(self, index, params=None, headers=None, **kwargs):
        """Fake index deletion"""
        documents_dict = self.__get_documents_dict()
        if index in documents_dict:
            del documents_dict[index]
        return {"acknowledged": True}

    @query_params("master_timeout", "timeout")
    def put_alias(self, index, name, body=None, params=None, headers=None, **kwargs):
        """Fake put alias"""
        aliases_dict = self.__get_aliases_dict()
        for idx in self._normalize_index_to_list(index):
            if idx not in aliases_dict:
                aliases_dict[idx] = {"aliases": {}}
            aliases_dict[idx]["aliases"][name] = {}
        return {"acknowledged": True}

    @query_params("allow_no_indices", "expand_wildcards", "ignore_unavailable", "local")
    def get_alias(self, index=None, name=None, params=None, headers=None, **kwargs):
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
    def delete_alias(self, index, name, params=None, headers=None, **kwargs):
        """Fake delete alias"""
        aliases_dict = self.__get_aliases_dict()
        for idx in self._normalize_index_to_list(index):
            if idx in aliases_dict and name in aliases_dict[idx]["aliases"]:
                del aliases_dict[idx]["aliases"][name]
        return {"acknowledged": True}

    def stats(self, index=None, metric=None, params=None, headers=None, **kwargs):
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

    @query_params("master_timeout", "timeout")
    def get_mapping(self, index=None, params=None, headers=None, **kwargs):
        """Fake get mapping"""
        mappings_dict = self.__get_mappings_dict()
        if index is None or index == "_all" or index == "*":
            return mappings_dict
        
        res = {}
        for idx in self._normalize_index_to_list(index):
            res[idx] = mappings_dict.get(idx, {"mappings": {}})
        return res

    @query_params("master_timeout", "timeout")
    def put_mapping(self, body, index=None, params=None, headers=None, **kwargs):
        """Fake put mapping"""
        mappings_dict = self.__get_mappings_dict()
        for idx in self._normalize_index_to_list(index):
            if idx not in mappings_dict:
                mappings_dict[idx] = {"mappings": {"properties": {}}}
            if "mappings" not in mappings_dict[idx]:
                mappings_dict[idx]["mappings"] = {"properties": {}}
            if "properties" not in mappings_dict[idx]["mappings"]:
                mappings_dict[idx]["mappings"]["properties"] = {}
            
            new_props = body.get("properties", body)
            mappings_dict[idx]["mappings"]["properties"].update(new_props)
        return {"acknowledged": True}

    @query_params("allow_no_indices", "expand_wildcards", "flat_settings", "ignore_unavailable", "local", "master_timeout")
    def get_settings(self, index=None, name=None, params=None, headers=None, **kwargs):
        """Fake get settings"""
        settings_dict = self.__get_settings_dict()
        if index is None or index == "_all" or index == "*":
            return settings_dict
        
        res = {}
        for idx in self._normalize_index_to_list(index):
            entry = settings_dict.get(idx, {"settings": {"index": {"number_of_shards": "1", "number_of_replicas": "1"}}})
            settings = entry.get("settings", {})
            
            # Real OpenSearch often nests these under "index" if not already
            if "index" not in settings:
                # If it's a flat dict of settings, or has other top level keys
                # for now let's just ensure we return it in a way that includes "index"
                new_settings = {"index": {}}
                for k, v in settings.items():
                    if k in ["number_of_shards", "number_of_replicas", "analysis", "provided_name", "creation_date", "uuid", "version"]:
                         new_settings["index"][k] = v
                    else:
                         new_settings["index"][k] = v
                settings = new_settings

            # Convert all values to strings for number_of_shards/replicas to match real behavior
            if "index" in settings:
                for k in ["number_of_shards", "number_of_replicas"]:
                    if k in settings["index"]:
                        settings["index"][k] = str(settings["index"][k])
            
            res[idx] = {"settings": settings}
        return res

    @query_params("allow_no_indices", "expand_wildcards", "flat_settings", "ignore_unavailable", "master_timeout", "preserve_existing", "timeout")
    def put_settings(self, body, index=None, params=None, headers=None, **kwargs):
        """Fake put settings"""
        settings_dict = self.__get_settings_dict()
        for idx in self._normalize_index_to_list(index):
            if idx not in settings_dict:
                settings_dict[idx] = {"settings": {"index": {}}}
            if "settings" not in settings_dict[idx]:
                settings_dict[idx]["settings"] = {"index": {}}
            if "index" not in settings_dict[idx]["settings"]:
                settings_dict[idx]["settings"]["index"] = {}
            
            new_settings = body.get("index", body)
            for k, v in new_settings.items():
                settings_dict[idx]["settings"]["index"][k] = str(v)
        return {"acknowledged": True}

    def analyze(self, body=None, index=None, params=None, headers=None, **kwargs):
        """Fake index analyze"""
        return {"tokens": []}

    def __get_documents_dict(self):
        """Get the documents dictionary"""
        return self.client._FakeIndicesClient__documents_dict

    def __get_mappings_dict(self):
        """Get the mappings dictionary"""
        return self.client._FakeIndicesClient__mappings_dict

    def __get_settings_dict(self):
        """Get the settings dictionary"""
        return self.client._FakeIndicesClient__settings_dict

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
