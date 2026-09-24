FROM python:3.11-slim-bookworm

# System dependencies (GDAL + PostGIS client + CV deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python package manager
RUN pip install --no-cache-dir uv

# Copy dependency file and install
COPY pyproject.toml .
RUN uv pip install --system --no-cache -e ".[dev]" 2>/dev/null || \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] python-multipart \
        sqlalchemy[asyncio] asyncpg geoalchemy2 alembic psycopg2-binary \
        "celery[redis]" redis \
        "python-jose[cryptography]" "passlib[bcrypt]" \
        shapely pyproj numpy scipy \
        aioboto3 boto3 \
        python-docx weasyprint jinja2 \
        pillow imagehash opencv-python-headless \
        onnxruntime \
        "pydantic>=2.7.0" pydantic-settings \
        httpx python-dateutil pyyaml structlog tenacity

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
