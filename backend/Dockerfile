FROM python:3.12-slim

# Install system dependencies: Git, Node.js, and npm (for Repomix CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy source code and documentation store
COPY backend/ /app/backend/
COPY content/ /app/content/

ENV PYTHONPATH=/app
ENV PORT=8000
ENV CONTENT_DIR=/app/content
ENV TEMP_DIR=/app/temp

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
