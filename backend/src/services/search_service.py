import logging
import uuid
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from backend.src.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, index_name: str = None):
        self.index_name = index_name or settings.AZURE_SEARCH_VIDEO_INDEX_NAME
        if not settings.AZURE_SEARCH_API_KEY or not settings.AZURE_SEARCH_ENDPOINT:
            logger.warning("Azure Search credentials missing. SearchService will not be available.")
            self.search_client = None
            return
        self.search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_API_KEY),
            index_name=self.index_name,
        )

    def hybrid_search(self, query: str, embedding: list, top: int = 5) -> list:
        """Perform a hybrid search (keyword + vector)."""
        try:
            from azure.search.documents.models import VectorizedQuery

            vector_query = VectorizedQuery(
                vector=embedding,
                k_nearest_neighbors=top,
                fields="text_embedding",
            )
            results = self.search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                top=top,
                select=["content", "category", "source_id"],
            )
            return [
                {
                    "content": r.get("content", ""),
                    "category": r.get("category", ""),
                    "source_id": r.get("source_id", ""),
                }
                for r in results
            ]
        except Exception:
            results = self.search_client.search(
                search_text=query,
                top=top,
                select=["content", "category", "source_id"],
            )
            return [
                {
                    "content": r.get("content", ""),
                    "category": r.get("category", ""),
                    "source_id": r.get("source_id", ""),
                }
                for r in results
            ]

    def upload_documents(self, documents: list) -> int:
        """
        Batch upload formatted documents to the search index.
        """
        if not documents:
            return 0

        batch_size = 50
        uploaded_count = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            results = self.search_client.upload_documents(documents=batch)
            uploaded_count += sum(1 for r in results if r.succeeded)

        logger.info(
            f"Successfully uploaded {uploaded_count} documents to index '{self.index_name}'"
        )
        return uploaded_count

    def format_document(
        self,
        content: str,
        filename: str,
        chunk_index: int,
        embedding: list,
        category: str,
    ) -> dict:
        """
        Helper to format a single document chunk for Azure AI Search.
        """
        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{filename}::{chunk_index}")),
            "source_id": filename.split(".")[0],  # strip extension
            "content": content,
            "category": category,
            "text_embedding": embedding,
        }
