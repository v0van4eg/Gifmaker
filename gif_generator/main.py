# gif_generator/main.py

from flask import Flask, request, jsonify, redirect, url_for, session, json
import os
import numpy as np
import imageio as imageio
from PIL import Image, ImageOps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
uploads_root = os.path.join(app.root_path, 'uploads')


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    """
    Генерирует GIF из загруженных изображений.

    Входные параметры:
    - X-Session-ID: Идентификатор сессии (передается в заголовках)
    - duration: Длительность кадра в миллисекундах (по умолчанию 200)
    - loop: Количество циклов воспроизведения GIF (по умолчанию 0)
    - resize: Новые размеры изображений в формате "ШxВ"

    Возвращает:
    - JSON с URL сгенерированного GIF или сообщение об ошибке
    """
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
    images = []
    for image_name in os.listdir(upload_folder):
        try:
            image_path = os.path.join(upload_folder, image_name)
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img)
            if resize:
                width, height = map(int, resize.split('x'))
                img = img.resize((width, height), Image.LANCZOS)
            images.append(np.array(img))
        except Exception as e:
            print(f"Error processing image {image_name}: {e}")
            continue
    if not images:
        return jsonify(error='No valid images uploaded'), 400
    try:
        with imageio.get_writer(gif_file, mode='I', duration=duration / 1000.0, loop=loop) as writer:
            for img in images:
                writer.append_data(img)
    except Exception as e:
        print(f"Error generating GIF: {e}")
        return jsonify(error='Error generating GIF'), 500
    return jsonify(success=True, gif_url=f'/static/uploads/{session_id}/animation.gif')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
