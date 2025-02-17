# image_processing/main.py

import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask import send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
uploads_root = os.path.join(app.root_path, 'uploads')


def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))


# Загрузка изображений
@app.route('/upload', methods=['POST'])
def upload():
    logger.info("-----------")
    logger.info("@@@ Мы внутри контейнера image_processing/upload")
    session_id = request.form.get('session_id')  # Получаем session_id из запроса
    if not session_id:
        return jsonify(error='Session ID not found'), 400
    logger.info(f'Session ID через request form: {session_id}')
    upload_folder = os.path.join(uploads_root, session_id)
    os.makedirs(upload_folder, exist_ok=True)
    files = request.files.getlist('files')
    if not files:
        return jsonify(error='No selected files'), 400
    new_filenames = []
    for file in files:
        if file and allowed_file(file.filename):
            unix_time = int(time.time())
            original_filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())[:8]
            filename = f"IMG_{unix_time}_{unique_id}_{original_filename}"
            logger.info(f"Filename: {filename}")
            file_path = os.path.join(upload_folder, filename)
            logger.info(f"File path: {file_path}")
            try:
                file.save(file_path)
                logger.info(f"Saved file {filename} to {file_path}")
                new_filenames.append(filename)
            except Exception as e:
                return jsonify(error=f'Failed to save file: {str(e)}'), 500
    return jsonify(success=True, filenames=new_filenames)


# Перестановка изображений
@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    logger.info("Мы внутри image_processing/reorder_images\nВыполняю перестановку изображений")
    session_id = request.form.get('session_id')
    image_order = request.form.get('image_order')
    logger.info(f'Session ID: {session_id}')
    logger.info(f'Image order: {image_order}')

    if not session_id or not image_order:
        return jsonify(error='Session ID or Image order not provided'), 400

    upload_folder = os.path.join(uploads_root, session_id)
    image_order = image_order.split(',')

    for idx, image_name in enumerate(image_order):
        old_path = os.path.join(upload_folder, image_name)
        new_path = os.path.join(upload_folder, f'{idx:04d}_{image_name}')
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            logger.info(f"Renamed {old_path} to {new_path}")

    for idx, image_name in enumerate(image_order):
        old_path = os.path.join(upload_folder, f'{idx:04d}_{image_name}')
        new_path = os.path.join(upload_folder, image_name)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            logger.info(f"Renamed {old_path} to {new_path}")

    return jsonify(success=True)


# Удаление изображения
@app.route('/remove_image', methods=['POST'])
def remove_image():
    logger.info("Мы внутри image_processing/remove_image\nВыполняю удаление изображения")
    session_id = request.form.get('session_id')
    image_name = request.form.get('image_name')
    logger.info(f'Session ID: {session_id}')
    logger.info(f'Image name: {image_name}')

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
