FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying code (layer cache)
COPY requirements/ requirements/
ARG REQUIREMENTS_FILE=development.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/${REQUIREMENTS_FILE}

# Copy project
COPY . .

# Create a non-root user for security
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default: development runserver (overridden in prod by gunicorn)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
