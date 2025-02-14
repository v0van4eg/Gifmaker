# Используем базовый образ Python
FROM python:3.9-slim
# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app
# Обновляем пакеты и устанавливаем необходимые инструменты
RUN apt update && apt upgrade -y
# Копируем файлы requirements.txt в контейнер
COPY requirements.txt .
# Устанавливаем зависимости Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
# Копируем весь код проекта в контейнер
COPY main.py .
# Устанавливаем переменную окружения для Flask (если используется)
ENV FLASK_APP=main.py
# Открываем порт для приложения (если необходимо)
EXPOSE 5004
# Команда для запуска приложения
CMD ["python", "main.py"]
