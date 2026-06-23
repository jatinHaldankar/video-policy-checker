import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    """
    Centralized configuration settings for the PharmaGuard AI application.
    """

    # Azure OpenAI
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")

    # Azure AI Search
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
    AZURE_SEARCH_VIDEO_INDEX_NAME = os.getenv(
        "AZURE_SEARCH_VIDEO_INDEX_NAME", "video-policy-checker-index"
    )

    # Azure Video Indexer
    AZURE_VI_NAME = os.getenv("AZURE_VI_NAME")
    AZURE_VI_LOCATION = os.getenv("AZURE_VI_LOCATION", "eastasia")
    AZURE_VI_ACCOUNT_ID = os.getenv("AZURE_VI_ACCOUNT_ID")
    AZURE_RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP")
    AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")

    # Azure Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv(
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
    )
    AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER_NAME = os.getenv(
        "AZURE_STORAGE_CONTAINER_NAME", "regulations"
    )

    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # App Settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150


settings = Settings()
