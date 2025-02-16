# Используем базовый образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

RUN apt update && apt upgrade -y

# Копируем файлы requirements.txt в контейнер
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY ./static ./static
COPY ./templates ./templates
COPY main.py .

# Устанавливаем переменную окружения для Flask (если используется)
ENV FLASK_APP=main.py

# Открываем порт для приложения (если необходимо)
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "main.py"]
