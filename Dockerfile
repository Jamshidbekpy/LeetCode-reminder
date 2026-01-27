FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# .env serverda/lokalda bor bo'ladi, docker-compose env_file orqali beriladi

CMD ["python", "-m", "app.bot"]
