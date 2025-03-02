# Используем базовый образ Python на основе Alpine
FROM python:3.9-alpine

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы requirements.txt в контейнер
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY upload.py .
# Устанавливаем переменную окружения для Flask (если используется)
ENV FLASK_APP=main.py
# Открываем порт для приложения (если необходимо)
EXPOSE 5001
# Команда для запуска приложения
CMD ["python", "upload.py"]
