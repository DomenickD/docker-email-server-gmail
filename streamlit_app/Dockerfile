FROM python:3.11-slim

# Install Python dependencies in a minimal image.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container.
COPY . .

EXPOSE 8501

# Launch the Streamlit app.  The `--server.address` flag
# binds to all interfaces so that the host can reach the
# service.  The port is specified via docker-compose.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]