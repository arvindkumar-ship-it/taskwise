from openai import OpenAI

from app.config import settings

# --- chat / extraction / planning ------------------------------------------
# Groq exposes an OpenAI-compatible endpoint, so this is just an OpenAI client
# pointed at a different base_url + key when llm_provider is "groq".

if settings.llm_provider == "groq":
    if not settings.groq_api_key:
        raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env")
    client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
    CHAT_MODEL = settings.groq_model
else:
    if not settings.openai_api_key:
        raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set in .env")
    client = OpenAI(api_key=settings.openai_api_key)
    CHAT_MODEL = settings.openai_model


# --- embeddings --------------------------------------------------------
# Groq has no embeddings endpoint. Default is a local ONNX model via fastembed
# (free, no API key, downloaded once into settings.model_cache_dir).
# Set EMBEDDING_PROVIDER=openai to use OpenAI embeddings instead.

_local_model = None
_openai_embedding_client = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from fastembed import TextEmbedding

        _local_model = TextEmbedding(
            model_name=settings.local_embedding_model,
            cache_dir=settings.model_cache_dir,
        )
    return _local_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    if settings.embedding_provider == "openai":
        global _openai_embedding_client
        if _openai_embedding_client is None:
            if not settings.openai_api_key:
                raise RuntimeError("EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set in .env")
            _openai_embedding_client = OpenAI(api_key=settings.openai_api_key)
        response = _openai_embedding_client.embeddings.create(
            model=settings.openai_embedding_model, input=texts
        )
        return [item.embedding for item in response.data]

    model = _get_local_model()
    return [vec.tolist() for vec in model.embed(texts)]