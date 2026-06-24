from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Centralized configuration settings for the PharmaGuard AI application.
    Reads from environment variables at runtime (not at class definition time).
    Automatically loads from .env file in local development.
    """

    # Azure OpenAI
    AZURE_OPENAI_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_EMBED_DEPLOYMENT: Optional[str] = None

    # Azure AI Search
    AZURE_SEARCH_ENDPOINT: Optional[str] = None
    AZURE_SEARCH_API_KEY: Optional[str] = None
    AZURE_SEARCH_VIDEO_INDEX_NAME: str = "video-policy-checker-index"

    # Azure Video Indexer
    AZURE_VI_NAME: Optional[str] = None
    AZURE_VI_LOCATION: str = "eastasia"
    AZURE_VI_ACCOUNT_ID: Optional[str] = None
    AZURE_RESOURCE_GROUP: Optional[str] = None
    AZURE_SUBSCRIPTION_ID: Optional[str] = None

    # Azure Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    AZURE_DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_CONTAINER_NAME: str = "pharma-regulations"

    # Database
    DATABASE_URL: Optional[str] = None

    # App Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"          # Ignore unknown env vars (e.g. system vars)
        case_sensitive = False    # AZURE_OPENAI_KEY == azure_openai_key


settings = Settings()
