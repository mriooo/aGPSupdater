FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Clone huami-token repository
RUN git clone https://codeberg.org/argrento/huami-token.git /app/huami-token

# Install huami-token dependencies
WORKDIR /app/huami-token
RUN uv pip install --system -e ".[dev]"

# Install bot dependencies
WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy bot files
COPY bot.py .
COPY .env.example .env

# Set permissions
RUN chmod +x bot.py

# Create non-root user
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Expose port (not needed for bot but good practice)
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
