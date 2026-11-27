import os

from opensearchpy import OpenSearch

opensearch = OpenSearch(os.environ["OPENSEARCH_URL"])

INDEXES = {
    "stories": {
        "settings": {"index.knn": True},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "source": {"type": "keyword"},
                "id": {"type": "keyword"},
                "title": {"type": "text"},
                "link": {"type": "keyword"},
                "summary": {"type": "text"},
                "published": {"type": "date"},
                "tags": {"type": "keyword"},
                "embedding": {"type": "knn_vector", "dimension": 1024, "space_type": "cosinesimil"},
            },
        },
    },
}

for name, template in INDEXES.items():
    opensearch.indices.put_index_template(name=name, body={"index_patterns": [f"{name}-*"], "template": template})
