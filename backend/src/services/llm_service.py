from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from backend.src.config import settings

class LLMService:
    def __init__(self):
        self.embedder = AzureOpenAIEmbeddings(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            azure_deployment=settings.AZURE_OPENAI_EMBED_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_VERSION,
        )
        self.llm = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_VERSION,
            temperature=0, # Better for compliance audits
        )

    def embed_text(self, text: str):
        return self.embedder.embed_query(text)

    def get_llm(self):
        return self.llm
