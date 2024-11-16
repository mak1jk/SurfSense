# Build stage
FROM python:3.11-bullseye as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libffi-dev \
    python3-dev \
    make \
    pkg-config \
    poppler-utils \
    sqlite3

# Install newer version of SQLite
RUN cd /tmp && \
    wget https://www.sqlite.org/2024/sqlite-autoconf-3450000.tar.gz && \
    tar xvfz sqlite-autoconf-3450000.tar.gz && \
    cd sqlite-autoconf-3450000 && \
    ./configure && \
    make && \
    make install && \
    cd .. && \
    rm -rf sqlite-autoconf-3450000* && \
    ldconfig

# Set working directory
WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Pre-install cffi and its dependencies using binary wheels
RUN pip install --upgrade pip && \
    pip install --no-build-isolation --only-binary :all: \
    cffi==1.15.1 \
    pycparser==2.21

# Install build dependencies and create wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir=/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim-bullseye

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libffi7 \
    poppler-utils \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy SQLite from builder
COPY --from=builder /usr/local/lib/libsqlite3* /usr/local/lib/
RUN ldconfig

# Install cffi first from pre-built wheel
RUN pip install --no-cache-dir cffi==1.15.1

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]
