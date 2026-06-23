"""
Create or update the Azure AI Search index for PharmaGuard AI.

Run:
    uv run python -m backend.src.utils.index
"""

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SemanticField,
    SearchFieldDataType,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    VectorSearch,
    HnswAlgorithmConfiguration,
    HnswParameters,
    VectorSearchProfile,
    SemanticSearch,
)
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os

load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_VIDEO_INDEX_NAME", "video-policy-checker-index")

credential = AzureKeyCredential(key)

# Vector search config
vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(
            name="hnsw-config",
            parameters=HnswParameters(
                m=16,
                ef_construction=400,
                ef_search=500,
                metric="cosine",
            ),
        ),
    ],
    profiles=[
        VectorSearchProfile(
            name="hnsw-profile",
            algorithm_configuration_name="hnsw-config",
        ),
    ],
)

# Semantic search config
semantic_config = SemanticConfiguration(
    name="pharma-semantic-config",
    prioritized_fields=SemanticPrioritizedFields(
        content_fields=[SemanticField(field_name="content")],
    ),
)
semantic_search = SemanticSearch(configurations=[semantic_config])

# Index fields
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SimpleField(name="source_id", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SearchableField(
        name="category",
        type=SearchFieldDataType.String,
        filterable=True,
        facetable=True,
        sortable=True,
    ),
    SearchField(
        name="text_embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        vector_search_dimensions=1536,
        vector_search_profile_name="hnsw-profile",
    ),
]

index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
    semantic_search=semantic_search,
)

index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
result = index_client.create_or_update_index(index)
print(f"[OK] Index '{result.name}' created/updated successfully.")

if __name__ == "__main__":
    pass
