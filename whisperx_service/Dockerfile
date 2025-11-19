FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including build tools for PyAV
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port
EXPOSE 8000

# Run the application with hypercorn (supports IPv6)
CMD ["hypercorn", "main:app", "--bind", "[::]:8000"]
