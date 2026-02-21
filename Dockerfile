# Base image
FROM python:3.14-alpine

# System libraries 
RUN apk upgrade --no-cache && \
    apk add --no-cache \
    libxml2 \
    libxslt

# UV installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Remove pip since we are using UV
RUN pip uninstall -y pip

# Working directory
WORKDIR /app

# Environment defaults
# Port and host can be overridden at runtime with -e PORT=… / -e HOST=…
ENV UV_PYTHON_DOWNLOADS=never \
    HOST=0.0.0.0 \
    PORT=8000

# Dependency installation
COPY pyproject.toml uv.lock ./

# Install all production dependencies using the lockfile
RUN uv sync --frozen --no-dev --no-cache

# Copy the application code into the container
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY run.py ./

# Make the volumes for uploads and outputs, so they can be mounted and reached from the host easily
VOLUME ["/app/data/uploads", "/app/data/outputs"]

# Expose the port the app runs on
EXPOSE 8000

# How to start the application
CMD ["uv", "run", "python", "run.py"]
