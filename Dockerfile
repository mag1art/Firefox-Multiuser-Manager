# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем зависимости
RUN apt update && apt install -y docker.io && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код сервера
COPY app /app
WORKDIR /app

# Запускаем сервер
CMD ["python", "server.py"]
