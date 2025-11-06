# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables can be passed at runtime
# Example: docker run -e DB_HOST=host -e DB_USER=user ...

# Run the application
CMD ["python", "main.py"]
