FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies including ffmpeg for video processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create downloads directory with proper permissions
RUN mkdir -p downloads && chmod 777 downloads

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["python", "run.py"]
