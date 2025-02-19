# image_processing/main.py

import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask import send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
uploads_root = os.path.join(app.root_path, 'uploads')


def allowed_file(filename):
    """
    Проверяет, является ли файл допустимого типа.

    Входные параметры:
    - filename: Имя файла

    Возвращает:
    - True, если файл допустимого типа, иначе False
    """
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))


# Загрузка изображений
@app.route('/upload', methods=['POST'])
def upload():
    """
    Обрабатывает загрузку изображений.

    Входные параметры:
    - X-Session-ID: Идентификатор сессии (передается в заголовках)
    - files: Файлы для загрузки

    Возвращает:
    - JSON с именами новых файлов или сообщение об ошибке
    """
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify(error='Session ID not in headers. not found'), 400
    logger.info(f'Полученный Session ID: {session_id}')
    upload_folder = os.path.join(uploads_root, session_id)
    logger.info(f'Каталог загрузки: {upload_folder}')
    if not os.path.exists(upload_folder):
        logger.info(f'Каталог загрузки не найден. Создаю каталог: {upload_folder}')
        os.makedirs(upload_folder)
    files = request.files.getlist('files')
    if not files:
        return jsonify(error='!!! No selected files'), 400
    new_filenames = []
    for file in files:
        logger.info(f'Файл: {file.filename}')
        if file and allowed_file(file.filename):
            unix_time = int(time.time())
            original_filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())[:8]
            filename = f"IMG_{unix_time}_{unique_id}_{original_filename}"
            logger.info(f"Старое имя файла: {original_filename}")
            logger.info(f"Новое имя файла: {filename}")
            file_path = os.path.join(upload_folder, filename)
            logger.info(f"Путь к файлу: {file_path}")
            try:
                file.save(file_path)
                logger.info(f"Файл {filename} сохранён в {file_path}")
                new_filenames.append(filename)
            except Exception as e:
                return jsonify(error=f'Failed to save file: {str(e)}'), 500
    return jsonify(success=True, filenames=new_filenames)


# Перестановка изображений
@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    logger.info("Мы внутри image_processing/reorder_images")
    logger.info("Выполняю перестановку изображений")
    session_id = request.headers.get('X-Session-ID')
    logger.info(f'Полученный Session ID: {session_id}')
    image_order_json = request.form.get('image_order')
    if not image_order_json:
        return jsonify(error='Image order not provided'), 400

    image_order = json.loads(image_order_json)
    logger.info(f'Полученный порядок изображений: {image_order}')
    upload_folder = os.path.join(uploads_root, session_id)

    temp_renames = {}
    try:
        for idx, image_name in sorted(image_order.items(), key=lambda x: int(x[0])):
            old_path = os.path.join(upload_folder, image_name)
            new_path = os.path.join(upload_folder, f'temp_{int(idx):04d}_{image_name}')  # Преобразуем idx в целое число
            if os.path.isfile(old_path):
                os.rename(old_path, new_path)
                temp_renames[new_path] = old_path
                logger.info(f"Renamed {old_path} to {new_path}")
            else:
                logger.warning(f"File {old_path} does not exist or is not a regular file")

        for new_path, old_path in temp_renames.items():
            final_path = os.path.join(upload_folder, os.path.basename(old_path))
            os.rename(new_path, final_path)
            logger.info(f"Renamed {new_path} to {final_path}")
        logger.info(f'Новый порядок изображений: {image_order}')

    except Exception as e:
        logger.error(f"Ошибка при перестановке изображений: {e}")
        # Если возникла ошибка, попытаться вернуть файлы в исходное состояние
        for new_path, old_path in temp_renames.items():
            if os.path.isfile(new_path):
                os.rename(new_path, old_path)
                logger.info(f"Восстановлен {new_path} в {old_path}")
        return jsonify(error='Не удалось переставить изображения'), 500

    return jsonify(success=True)

# Удаление изображения
@app.route('/remove_image', methods=['POST'])
def remove_image():
    """
    Удаляет изображение.
    Входные параметры:
    - X-Session-ID: Идентификатор сессии (передается в заголовках)
    - image_name: Имя файла для удаления
    Возвращает:
    - JSON с успешным статусом или сообщением об ошибке
    """
    logger.info("Мы внутри image_processing/remove_image\nВыполняю удаление изображения")
    session_id = request.headers.get('X-Session-ID')  # Получаем session_id из заголовков

    image_name = request.form.get('image_name')
    logger.info(f'Session ID: {session_id}')
    logger.info(f'File name: {image_name}')

    if not session_id or not image_name:
        return jsonify(error='Session ID or Image name not provided'), 400

    upload_folder = os.path.join(uploads_root, session_id)
    image_path = os.path.join(upload_folder, image_name)

    if os.path.exists(image_path):
        try:
            os.remove(image_path)
            logger.info(f"Deleted image {image_name} from {image_path}")
            return jsonify(success=True)
        except Exception as e:
            logger.error(f"Error deleting image {image_name}: {e}")
            return jsonify(error=f'Failed to delete image: {str(e)}'), 500
    else:
        logger.error(f"Image {image_name} not found at {image_path}")
        return jsonify(error='Image not found'), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
