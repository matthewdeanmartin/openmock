----

ISSUE 1

We're using openmock to replace slow integration tests in a project that relies heavily on index aliases (versioned indices with alias swaps). Issue #1 mentioned get_alias being missing - this is the full version of that ask.

Methods we'd need on the indices client:

    put_alias, delete_alias, exists_alias, get_alias (with wildcard support), update_aliases (atomic add/remove)

Alias names would also need to resolve in existing operations - e.g. search(index="my-alias") should find documents in the backing index. Same for get, count, delete, cat.indices, cat.aliases, etc.



---
ISSUE 2


Hello, I've recently discovered an issue with the aggregation building in the search function in fake_opensearch.py...

It seems like this method does not support all types of aggregations. More specifically, I'm aggregating using the diversified_sampler function in a query like this

{
  "size": 0,
  "aggs": {
    "diverse_categories": {
      "diversified_sampler": {
        "field": "category_id"
      },
      "aggs": {
        "top_products": {
          "top_hits": {
            "_source": {
              "includes": ["product_name", "price", "category_id"]
            },
            "size": 3
          }
        }
      }
    }
  }
}

and expecting top_hits under the top_products aggregation in return. However, the expected return from FakeOpenSearch does not match the call from the actual OpenSearch client (from opensearchpy).

It should be noted that we have not yet migrated from ElasticSearch to OpenSearch, so I may be missing something. However, I thought it'd still be good to note this issue here in case someone has time to look into it. Thanks in advance!

----

ISSUE 3


Hello,

I wanted to report an issue on a few missing methods and parameters in openmock when compared to opensearchpy.

e.g. openmock does not have a delete_by_query method for OpenSearch mocked client.

e.g. search method is missing track_total_hits for the OpenSearch mocked client.

e.g. The mocked indices client does not have a get_alias method.

I ran into these while using openmock, but I believe there will be more. Is there any plan of addressing them? I did not see a contributing guideline, and thus, didn't want to push code without knowing the correct steps. I am happy to write code to address these gaps.