FROM python:3.11-slim

WORKDIR /app

# Embedding model is baked into the image so the first request after a deploy or
# a cold start does not have to download it (container disk is ephemeral on
# free hosts).
ENV MODEL_CACHE_DIR=/app/models \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/app/models')"

COPY . .
RUN mkdir -p /app/data

EXPOSE 8000

# Render injects $PORT (10000 by default); locally it falls back to 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]