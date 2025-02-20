# gif_generator/main.py

from flask import Flask, request, jsonify, session
import logging
import os
import numpy as np
import imageio as imageio
from PIL import Image, ImageOps
import json
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
uploads_root = os.path.join(app.root_path, 'uploads')


def optimize_gif(input_path, output_path):
    """
    Оптимизирует GIF с использованием gifsicle.
    """
    try:
        subprocess.run(['gifsicle', '--optimize=3', '--colors', '256', input_path, '-o', output_path], check=True)
        logger.info(f"GIF успешно оптимизирован: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при оптимизации GIF: {e}")


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    logger.info(f"@@@ Мы внутри Запускаем генератор GIF")
    session_id = request.headers.get('X-Session-ID')
    logger.info(f'Session ID через request header: {session_id}')
    if not session_id:
        return jsonify(error='Session ID not found'), 400
    logger.info(f'Session ID: {session_id}')
    upload_folder = os.path.join(uploads_root, session_id)
    gif_file = os.path.join(upload_folder, 'animation.gif')
    duration = int(request.form.get('duration', 200))
    logger.info(f'Duration: {duration}')
    loop = int(request.form.get('loop', 0))
    logger.info(f'Loop: {loop}')
    resize = request.form.get('resize')
    logger.info(f'Resize: {resize}')

    # Получаем порядок изображений из данных запроса
    image_order_json = request.form.get('image_order')
    if not image_order_json:
        return jsonify(error='No image order found in request'), 400

    image_order = json.loads(image_order_json)
    logger.info(f'Полученный порядок изображений: {image_order}')

    images = []
    for idx in sorted(image_order.keys(), key=int):
        image_name = image_order[idx]
        try:
            image_path = os.path.join(upload_folder, image_name)
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img)
            if resize:
                width, height = map(int, resize.split('x'))
                img = img.resize((width, height), Image.LANCZOS)
            images.append(np.array(img))
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения {image_name}: {e}")
            continue

    if not images:
        return jsonify(error='No valid images uploaded'), 400

    try:
        temp_gif_file = os.path.join(upload_folder, 'temp_animation.gif')
        with imageio.get_writer(temp_gif_file, mode='I', duration=duration / 1000.0, loop=loop) as writer:
            for img in images:
                writer.append_data(img)

        # Оптимизируем GIF
        optimize_gif(temp_gif_file, gif_file)
        os.remove(temp_gif_file)  # Удаляем временный файл

    except Exception as e:
        logger.error(f"Ошибка при генерации GIF: {e}")
        return jsonify(error='Ошибка при генерации GIF'), 500

    return jsonify(success=True, gif_url=f'/uploads/{session_id}/animation.gif')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
