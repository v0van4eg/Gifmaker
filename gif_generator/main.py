from flask import Flask, request, jsonify
import logging
import os
import numpy as np
import imageio as imageio
from PIL import Image, ImageOps
import subprocess
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

redis_host = os.getenv('REDIS_HOST', 'redis')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

uploads_root = os.path.join(app.root_path, 'uploads')


def optimize_gif(input_path, output_path):
    try:
        subprocess.run(['gifsicle', '--optimize=3', '--colors', '256', input_path, '-o', output_path], check=True)
        logger.info(f"GIF успешно оптимизирован: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при оптимизации GIF: {e}")


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    """
    Генерирует GIF на основе данных из Redis.
    """
    # Получаем session_id из заголовков запроса
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        logger.error("Session ID не найден в заголовках запроса")
        return jsonify(error='Session ID not found'), 400
    logger.info(f"Получен Session ID: {session_id}")

    # Получаем параметры для генерации GIF из запроса
    duration = int(request.form.get('duration', 200))
    loop = int(request.form.get('loop', 0))
    resize = request.form.get('resize')

    # Получаем порядок изображений из Redis
    image_order = redis_client.hgetall(f'session:{session_id}:images')
    if not image_order:
        logger.error("Порядок изображений не найден в Redis")
        return jsonify(error='No image order found in Redis'), 400

    # Декодируем ключи и значения из bytes в строки
    decoded_image_order = {key.decode('utf-8'): value.decode('utf-8') for key, value in image_order.items()}
    logger.info(f"Декодированный порядок изображений: {decoded_image_order}")

    # Определяем папку для загрузок и путь к GIF-файлу
    upload_folder = os.path.join(uploads_root, session_id)
    gif_file = os.path.join(upload_folder, 'animation.gif')
    logger.info(f"Папка для загрузок: {upload_folder}")
    logger.info(f"Путь к GIF-файлу: {gif_file}")

    # Обрабатываем изображения
    logger.info("Начало обработки изображений")
    images = []
    for idx in sorted(decoded_image_order.keys(), key=int):
        image_name = decoded_image_order[idx]
        logger.info(f"Обработка изображения: {image_name}")

        try:
            image_path = os.path.join(upload_folder, image_name)
            logger.info(f"Путь к изображению: {image_path}")

            # Открываем изображение и применяем EXIF-ориентацию
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img)
            logger.info(f"Изображение {image_name} успешно открыто и обработано")

            # Изменяем размер изображения, если указан параметр resize
            if resize:
                width, height = map(int, resize.split('x'))
                logger.info(f"Изменение размера изображения на {width}x{height}")
                img = img.resize((width, height), Image.LANCZOS)

            # Преобразуем изображение в массив numpy и добавляем в список
            images.append(np.array(img))
            logger.info(f"Изображение {image_name} успешно добавлено в список для генерации GIF")

        except Exception as e:
            logger.error(f"Ошибка при обработке изображения {image_name}: {e}")
            continue

    # Проверяем, есть ли изображения для генерации GIF
    if not images:
        logger.error("Нет допустимых изображений для генерации GIF")
        return jsonify(error='No valid images uploaded'), 400
    logger.info(f"Количество изображений для генерации GIF: {len(images)}")

    # Генерация GIF
    logger.info("Начало генерации GIF")
    try:
        temp_gif_file = os.path.join(upload_folder, 'temp_animation.gif')
        logger.info(f"Временный файл GIF: {temp_gif_file}")

        # Создаем GIF с использованием imageio
        with imageio.get_writer(temp_gif_file, mode='I', duration=duration / 1000.0, loop=loop) as writer:
            for img in images:
                writer.append_data(img)
        logger.info("GIF успешно сгенерирован")

        # Оптимизируем GIF с помощью gifsicle
        logger.info("Оптимизация GIF с помощью gifsicle")
        optimize_gif(temp_gif_file, gif_file)

        # Удаляем временный файл
        os.remove(temp_gif_file)
        logger.info(f"Временный файл {temp_gif_file} удален")

    except Exception as e:
        logger.error(f"Ошибка при генерации GIF: {e}")
        return jsonify(error='Ошибка при генерации GIF'), 500

    # Возвращаем успешный результат
    logger.info(f"GIF успешно создан и доступен по адресу: /uploads/{session_id}/animation.gif")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
