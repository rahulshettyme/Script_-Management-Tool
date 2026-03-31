FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_VERSION=20

RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    libgdal-dev \
    libproj-dev \
    libspatialindex-dev \
    build-essential \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY package.json ./
RUN npm install --ignore-scripts

COPY . .

EXPOSE 3001

CMD ["npm", "start"]