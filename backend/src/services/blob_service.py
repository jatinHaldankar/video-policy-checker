import os
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


class BlobService:
    """
    Service for interacting with Azure Blob Storage.
    """

    def __init__(self):
        from backend.src.config import settings
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        if not connection_string:
            logger.warning(
                "AZURE_CONNECTION_STRING not found in environment variables."
            )
            self.blob_service_client = None
        else:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    connection_string
                )
            except Exception as e:
                logger.error(f"Failed to initialize BlobServiceClient with provided connection string: {e}")
                self.blob_service_client = None

    def list_blobs(self, container_name: str):
        """
        List all blobs in a given container.
        """
        if not self.blob_service_client:
            raise ValueError("BlobServiceClient is not initialized.")

        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            raise ValueError(f"Container '{container_name}' does not exist.")

        return container_client.list_blobs()

    def download_blob(self, container_name: str, blob_name: str) -> bytes:
        """
        Download a blob's content as bytes.
        """
        if not self.blob_service_client:
            raise ValueError("BlobServiceClient is not initialized.")

        blob_client = self.blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        return blob_client.download_blob().readall()

    def upload_blob(self, container_name: str, blob_name: str, content: bytes) -> str:
        """
        Upload bytes to a blob. Returns the blob name.
        """
        if not self.blob_service_client:
            raise ValueError("BlobServiceClient is not initialized.")

        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()

        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(content, overwrite=True)
        return blob_name

    def delete_blob(self, container_name: str, blob_name: str):
        """
        Delete a blob from a container.
        """
        if not self.blob_service_client:
            return

        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            blob_client.delete_blob()
            logger.info(f"Deleted blob: {blob_name} from container: {container_name}")
        except Exception as e:
            logger.warning(f"Failed to delete blob {blob_name}: {e}")

    def generate_sas_url(
        self, container_name: str, blob_name: str, expiry_hours: int = 2
    ) -> str:
        """
        Generate a temporary SAS URL for a private blob.
        This allows Azure Video Indexer to download the file securely.
        """
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from datetime import datetime, timedelta, timezone

        if not self.blob_service_client:
            raise ValueError("BlobServiceClient is not initialized.")

        sas_token = generate_blob_sas(
            account_name=self.blob_service_client.account_name,
            account_key=self.blob_service_client.credential.account_key,
            container_name=container_name,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        )

        return f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
