import logging
from typing import Dict

from backend.src.config import settings
from backend.src.services.blob_service import BlobService
from backend.src.services.doc_intel_service import DocumentIntelligenceService
from backend.src.services.search_service import SearchService
from backend.src.services.text_processor import TextProcessorService
from backend.src.services.llm_service import LLMService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DocumentIngester:
    """
    Orchestrator for ingesting regulatory documents from Azure Blob Storage into AI Search.
    """

    def __init__(self):
        self.blob_service = BlobService()
        self.doc_intel_service = DocumentIntelligenceService()
        self.search_service = SearchService()
        self.text_processor = TextProcessorService()
        self.llm_service = LLMService()

    def _determine_category(self, filename: str) -> str:
        fname = filename.lower()
        if "fda" in fname or "opdp" in fname:
            return "FDA"
        if "ich" in fname:
            return "ICH"
        if "mlr" in fname or "checklist" in fname:
            return "MLR"
        if "ema" in fname or "europe" in fname:
            return "EMA"
        if "ftc" in fname:
            return "FTC"
        if "health_canada" in fname or "canada" in fname:
            return "Health Canada"
        if "who" in fname:
            return "WHO"
        if "pharma" in fname or "phrmа" in fname:
            return "PhRMA"
        return "Custom"

    def _ingest_bytes(self, content: bytes, filename: str) -> int:
        """Processes raw bytes: Extract -> Chunk -> Embed -> Index."""
        logger.info(f"Processing: {filename}")

        text = self.doc_intel_service.extract_text(content, filename)
        if not text.strip():
            logger.warning(f"No text extracted from {filename} — skipping.")
            return 0

        chunks = self.text_processor.chunk_text(text, source_name=filename)
        category = self._determine_category(filename)

        formatted_docs = []
        for chunk in chunks:
            try:
                embedding = self.llm_service.embed_text(chunk["text"])
                doc = self.search_service.format_document(
                    content=chunk["text"],
                    filename=filename,
                    chunk_index=chunk["chunk_index"],
                    embedding=embedding,
                    category=category,
                )
                formatted_docs.append(doc)
            except Exception as e:
                logger.error(f"  Embedding error on chunk {chunk['chunk_index']}: {e}")

        return self.search_service.upload_documents(formatted_docs)

    def ingest_from_blob_container(self, container_name: str) -> Dict[str, int]:
        """Ingest all supported documents from an Azure Blob container."""
        supported_extensions = {
            ".txt",
            ".pdf",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".xlsx",
            ".xls",
            ".html",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
        }

        results = {}
        total_chunks = 0

        logger.info(f"Orchestrating ingestion from container: {container_name}")
        try:
            blobs = self.blob_service.list_blobs(container_name)
            for blob in blobs:
                if any(blob.name.lower().endswith(ext) for ext in supported_extensions):
                    logger.info(f"Found blob: {blob.name}")
                    content = self.blob_service.download_blob(container_name, blob.name)

                    count = self._ingest_bytes(content, blob.name)
                    results[blob.name] = count
                    total_chunks += count
        except Exception as e:
            logger.error(f"Ingestion orchestration failed: {e}")
            raise

        logger.info(
            f"\n Ingestion complete: {total_chunks} chunks across {len(results)} files."
        )
        return results


if __name__ == "__main__":
    container = settings.AZURE_STORAGE_CONTAINER_NAME
    if not container:
        logger.error("AZURE_STORAGE_CONTAINER_NAME not found in environment.")
    else:
        ingester = DocumentIngester()
        try:
            ingester.ingest_from_blob_container(container)
        except Exception as e:
            logger.error(f"Manual ingestion failed: {e}")
