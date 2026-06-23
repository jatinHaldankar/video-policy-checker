import os
import logging
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

logger = logging.getLogger(__name__)

class DocumentIntelligenceService:
    """
    Service for interacting with Azure Document Intelligence.
    """

    def __init__(self):
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not endpoint or not key:
            logger.warning("Azure Document Intelligence credentials not found in environment.")
            self.client = None
        else:
            self.client = DocumentIntelligenceClient(
                endpoint=endpoint, credential=AzureKeyCredential(key)
            )

    def extract_text(self, content: bytes, filename: str) -> str:
        """
        Extract text from document bytes using the prebuilt-layout model.
        Falls back to UTF-8 decoding for .txt files.
        """
        if not self.client:
            raise ValueError("DocumentIntelligenceClient is not initialized.")

        suffix = os.path.splitext(filename)[1].lower()

        # Handle plain text files natively for speed/cost
        if suffix == ".txt":
            try:
                return content.decode("utf-8", errors="replace")
            except Exception as e:
                logger.error(f"Failed to decode TXT file {filename}: {e}")
                return ""

        logger.info(f"Extracting text from {filename} via Azure Document Intelligence...")
        try:
            poller = self.client.begin_analyze_document(
                "prebuilt-layout", 
                body=content, 
                output_content_format="markdown"
            )
            result = poller.result()
            return result.content
        except Exception as e:
            logger.error(f"Document Intelligence extraction failed for {filename}: {e}")
            return ""
