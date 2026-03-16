FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies: gcc for psycopg2, curl for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium for SPA scraping
RUN playwright install chromium --with-deps

COPY . /app/

# Build the Vue admin SPA + widget
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && cd /app/widget-vue \
    && npm ci \
    && npm run build

# Collect Django static files
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000
