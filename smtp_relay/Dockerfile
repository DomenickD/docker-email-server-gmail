FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies from requirements.txt
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app.py /app/app.py
RUN mkdir -p /app/mail_store

EXPOSE 25 8025

CMD ["python", "app.py"]
