FROM python:3.12-slim

# Copy uv binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files and install
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen

# Create the faiss_index directory
RUN mkdir -p /app/faiss_index

# Copy FastAPI app and engine files
COPY api.py engine2.py /app/

# Explicitly copy the FAISS index files
COPY faiss_index/index.faiss faiss_index/index.pkl /app/faiss_index/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Start FastAPI with Uvicorn
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]