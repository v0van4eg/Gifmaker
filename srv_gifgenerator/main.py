from flask import Flask, request, jsonify  # Flask для создания веб-приложения
import logging  # Для логирования событий
import os  # Для работы с файловой системой
import numpy as np  # Для работы с массивами изображений
import imageio as imageio  # Для создания GIF
from PIL import Image, ImageOps  # Для обработки изображений
import json  # Для работы с JSON
import subprocess  # Для вызова внешних команд (gifsicle)
import redis

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)  # Устанавливаем уровень логирования на INFO
logger = logging.getLogger(__name__)  # Создаем логгер для текущего модуля

# Создаем Flask-приложение
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для подписи сессий

# Путь к корневой директории для загрузок
uploads_root = os.path.join(app.root_path, 'uploads')

# Подключение к Redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

def optimize_gif(input_path, output_path):
    try:
        # Выполняем команду gifsicle для оптимизации GIF
        subprocess.run(['gifsicle', '--optimize=3', '--colors', '256', input_path, '-o', output_path], check=True)
        logger.info(f"GIF успешно оптимизирован: {output_path}")
    except subprocess.CalledProcessError as e:
        # Логируем ошибку, если оптимизация не удалась
        logger.error(f"Ошибка при оптимизации GIF: {e}")

@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    logger.info("@@@ Запуск генерации GIF")
    # Получаем session_id из заголовков запроса
    session_id = request.headers.get('X-Session-ID')
    logger.info(f'Session ID из заголовков запроса: {session_id}')
    # Проверяем, что session_id передан
    if not session_id:
        logger.error("Session ID не найден в запросе")
        return jsonify(error='Session ID not found'), 400
    logger.info(f'Используемый Session ID: {session_id}')
    # Путь к папке загрузок для текущей сессии
    upload_folder = os.path.join(uploads_root, session_id)
    # Путь к итоговому GIF-файлу
    gif_file = os.path.join(upload_folder, 'animation.gif')
    # Получаем параметры для генерации GIF из формы запроса
    duration = int(request.form.get('duration', 200))  # Длительность кадра в миллисекундах
    logger.info(f'Длительность кадра: {duration} мс')
    loop = int(request.form.get('loop', 0))  # Количество циклов (0 для бесконечного цикла)
    logger.info(f'Количество циклов: {loop}')
    resize = request.form.get('resize')  # Размер изображения (например, "320x240")
    logger.info(f'Размер изображения: {resize}')

    # Получаем порядок изображений из REDIS для текущей сессии
    redis_key = f"session:{session_id}:order"
    if redis_client.exists(redis_key):
        order = redis_client.lrange(redis_key, 0, -1)
        order = [item.decode('utf-8') for item in order]
        logger.info(f'Полученный порядок изображений: {order}')
    else:
        logger.error("No images found for session")
        return jsonify(error='No images found for session'), 400

    # Список для хранения обработанных изображений
    images = []
    # Обрабатываем каждое изображение в соответствии с порядком
    for image_name in order:
        try:
            # Полный путь к изображению
            image_path = os.path.join(upload_folder, image_name)
            logger.info(f'Обработка изображения: {image_path}')
            # Открываем изображение с помощью Pillow
            img = Image.open(image_path)
            # Корректируем ориентацию изображения (если необходимо)
            img = ImageOps.exif_transpose(img)
            # Если указан размер, изменяем размер изображения
            if resize:
                width, height = map(int, resize.split('x'))
                logger.info(f'Изменение размера изображения на {width}x{height}')
                img = img.resize((width, height), Image.LANCZOS)
            # Преобразуем изображение в массив numpy и добавляем в список
            images.append(np.array(img))
        except Exception as e:
            # Логируем ошибку, если изображение не удалось обработать
            logger.error(f"Ошибка при обработке изображения {image_name}: {e}")
            continue

    # Проверяем, что есть хотя бы одно изображение для генерации GIF
    if not images:
        logger.error("Нет допустимых изображений для генерации GIF")
        return jsonify(error='No valid images uploaded'), 400

    try:
        # Создаем временный файл для GIF
        temp_gif_file = os.path.join(upload_folder, 'temp_animation.gif')
        logger.info(f'Создание временного GIF-файла: {temp_gif_file}')
        # Генерируем GIF с помощью imageio
        with imageio.get_writer(temp_gif_file, mode='I', duration=duration / 1000.0, loop=loop) as writer:
            for img in images:
                writer.append_data(img)
        # Оптимизируем GIF с помощью gifsicle
        logger.info(f'Оптимизация GIF: {temp_gif_file} -> {gif_file}')
        optimize_gif(temp_gif_file, gif_file)
        # Удаляем временный файл
        os.remove(temp_gif_file)
        logger.info(f'Временный файл {temp_gif_file} удален')
    except Exception as e:
        # Логируем ошибку, если генерация GIF не удалась
        logger.error(f"Ошибка при генерации GIF: {e}")
        return jsonify(error='Ошибка при генерации GIF'), 500

    # Возвращаем успешный результат и URL сгенерированного GIF
    logger.info(f'GIF успешно сгенерирован: {gif_file}')
    return jsonify(success=True, gif_url=f'/uploads/{session_id}/animation.gif')

if __name__ == '__main__':
    # Запускаем Flask-приложение
    logger.info("Запуск Flask-приложения на порту 5002")
    app.run(debug=True, host='0.0.0.0', port=5002)