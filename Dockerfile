# Use Python 3.9 Slim as the base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Node.js
# We need curl to download Node setup, and build-essential for potential python package compilation
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify versions
RUN node -v && npm -v && python --version

# Copy Python Requirements
COPY requirements.txt .

# Install Python Dependencies
# --no-cache-dir to keep image light
RUN pip install --no-cache-dir -r requirements.txt

# Copy Node.js Requirements
COPY package*.json ./

# Install Node.js Dependencies
RUN npm install

# Copy Application Source Code
COPY . .

# Expose the application port
EXPOSE 3001

# Start the application
CMD ["npm", "start"]
