# srv_upload/upload.py


import time
from flask import Flask, request, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
import logging
import redis

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)  # Устанавливаем уровень логирования в DEBUG для более подробного логирования
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для подписи сессии
uploads_root = os.path.join(app.root_path, 'uploads')  # Путь к директории загрузок

# Подключение к Redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

def allowed_file(filename):
    logger.debug(f"Проверка допустимости файла: {filename}")
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))

# Загрузка изображений
@app.route('/upload', methods=['POST'])
def upload():
    """
    Обрабатывает загрузку изображений.

    Входные параметры:
    - files: Файлы для загрузки

    Возвращает:
    - JSON с именами новых файлов или сообщение об ошибке
    """
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        logger.error("Session ID не найден в заголовках")
        return jsonify(error='Session ID not in headers. not found'), 400

    logger.info(f'Полученный Session ID: {session_id}')
    upload_folder = os.path.join(uploads_root, session_id)
    logger.info(f'Каталог загрузки: {upload_folder}')


    # Получаем файлы из запроса
    files = request.files.getlist('files')
    if not files:
        logger.error("Нет выбранных файлов")
        return jsonify(error='No selected files'), 400

    new_order = []
    for file in files:
        logger.debug(f'Файл: {file.filename}')
        if file and allowed_file(file.filename):
            # Генерируем уникальное имя файла
            unix_time = int(time.time())
            original_filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())[:8]
            filename = f"IMG_{unix_time}_{unique_id}_{original_filename}"
            logger.info(f"Старое имя файла: {original_filename}")
            logger.info(f"Новое имя файла: {filename}")

            # Сохраняем файл
            file_path = os.path.join(upload_folder, filename)
            logger.info(f"Путь к файлу: {file_path}")
            try:
                file.save(file_path)
                logger.debug(f"Файл {filename} сохранён в {file_path}")
                new_order.append(filename)
            except Exception as e:
                logger.error(f'Ошибка при сохранении файла: {str(e)}')
                return jsonify(error=f'Failed to save file: {str(e)}'), 500

    # Сохраняем порядок файлов в Redis
    redis_key = f"session:{session_id}:order"
    if redis_client.exists(redis_key):
        current_order = redis_client.lrange(redis_key, 0, -1)
        current_order = [item.decode('utf-8') for item in current_order]
        current_order.extend(new_order)
        redis_client.delete(redis_key)
        redis_client.rpush(redis_key, *current_order)
    else:
        redis_client.rpush(redis_key, *new_order)

    logger.info(f'Новые имена файлов:')
    for filename in new_order:
        logger.info(f'  - {filename}')
    return jsonify(success=True, filenames=new_order)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Запускаем Flask-приложение
