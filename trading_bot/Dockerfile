# SafeTrendBot V5 — Dockerfile
# Usage: docker build -t safetrendbot:v5 . && docker run -p 8080:8080 safetrendbot:v5

FROM python:3.11-slim

# Dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    libfontconfig1 \
    libdbus-1-3 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xkb1 \
    xvfb \
    espeak \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ML optionnel
RUN pip install --no-cache-dir scikit-learn hmmlearn || true

# Copie du code
COPY . .

# Répertoire données
RUN mkdir -p /data && ln -s /data /app/data

# Variable d'environnement
ENV PYTHONPATH=/app
ENV DISPLAY=:99
ENV SAFETRENDBOT_MODE=headless

# Expose le Web Dashboard
EXPOSE 8080

# Script d'entrée
RUN echo '#!/bin/bash\n\
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &\n\
python headless.py --paper\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
