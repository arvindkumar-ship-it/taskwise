from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI is now optional. It is only needed if LLM_PROVIDER=openai
    # or EMBEDDING_PROVIDER=openai.
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Chat/extraction/planning can run on Groq instead of OpenAI (free tier).
    # NOTE: the code uses strict json_schema output, which on Groq only works
    # with openai/gpt-oss-20b and openai/gpt-oss-120b. llama-3.3-70b will 400.
    llm_provider: str = "openai"  # "openai" or "groq"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"

    # Embeddings: "local" (fastembed, free, runs on your CPU, no API key)
    # or "openai".
    embedding_provider: str = "local"
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"
    model_cache_dir: str = "./data/models"

    database_path: str = "./data/app.db"

    sendgrid_api_key: str | None = None
    email_from: str | None = None


settings = Settings()

# Make sure the data directory exists before anything tries to write into it.
Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
Path(settings.model_cache_dir).mkdir(parents=True, exist_ok=True)