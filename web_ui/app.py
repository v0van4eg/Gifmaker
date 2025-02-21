# web_ui/app.py

from flask import send_from_directory
from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import uuid
import os
import logging
import redis
import json
import shutil
import requests
from flask_session import Session  # Импортируем Flask-Session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для подписи сессий
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://redis:6379/0')  # Подключение к Redis

Session(app)

# Подключение к Redis для хранения данных
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

# Настройка логирования в консоль
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Логи будут выводиться в консоль
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Фильтр допустимых форматов файлов
def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'tiff'))


# Корневая директория для загрузок
uploads_root = os.path.join(app.root_path, 'uploads')


@app.route('/uploads/<path:filename>')
def get_uploaded_file(filename):
    """
    Возвращает файл из папки загрузок.
    """
    session_id = session.get('session_id')
    if not session_id:
        logger.error(f"Ошибка: Session ID не найден для файла: {filename}")
        return jsonify(error='Session ID not found'), 404

    upload_folder = os.path.join(uploads_root, session_id)
    logger.info(f"Попытка получить файл: {filename} из сессии: {session_id}")
    return send_from_directory(upload_folder, filename)


@app.route('/new_session', methods=['GET'])
def new_session():
    """
    Создает новую сессию, удаляя старые данные и файлы.
    """
    logger.info('Очистка старой сессии и создание новой сессии.')
    session_id = session.get('session_id')
    if session_id:
        logger.info(f"Очистка старой сессии: {session_id}")
        redis_client.delete(f'session:{session_id}:images')

        session_folder = os.path.join(uploads_root, session_id)
        if os.path.exists(session_folder):
            try:
                shutil.rmtree(session_folder)
                logger.info(f"Папка сессии удалена: {session_folder}")
            except Exception as e:
                logger.error(f"Ошибка при удалении папки сессии: {e}")
                return jsonify(error='Failed to delete session folder'), 500

    session.clear()
    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id
    logger.info(f"Создана новая сессия: {new_session_id}")

    upload_folder = os.path.join(uploads_root, new_session_id)
    try:
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f"Создана папка для загрузок: {upload_folder}")
    except Exception as e:
        logger.error(f"Ошибка при создании папки для загрузок: {e}")
        return jsonify(error='Failed to create upload directory'), 500

    # Редирект на главную страницу (индекс)
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Главная страница приложения.
    Отображает загруженные изображения и форму для создания GIF.
    """
    logger.info('Главная страница приложения.')
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        logger.info(f"Создана новая сессия: {session_id}")

        upload_folder = os.path.join(uploads_root, session_id)
        try:
            os.makedirs(upload_folder, exist_ok=True)
            logger.info(f"Создана папка для загрузок: {upload_folder}")
        except Exception as e:
            logger.error(f"Ошибка при создании папки для загрузок: {e}")
            return jsonify(error='Failed to create upload directory'), 500

    image_order = redis_client.hgetall(f'session:{session_id}:images')
    if image_order:
        decoded_image_order = {key.decode('utf-8'): value.decode('utf-8') for key, value in image_order.items()}
        images = [decoded_image_order[key] for key in sorted(decoded_image_order.keys(), key=int)]
        logger.info(f"Получены изображения для сессии: {session_id}")
    else:
        images = []
        logger.info(f"Изображения НЕ найдены для сессии: {session_id}")

    gif_file = os.path.join(uploads_root, session_id, 'animation.gif')
    gif_exists = os.path.exists(gif_file)
    logger.info(f"GIF-файл существует: {gif_exists}")

    if request.method == 'POST':
        files = request.files.getlist('files')
        if files:
            new_filenames = []
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(uploads_root, session_id, filename)
                    file.save(file_path)
                    new_filenames.append(filename)
                    logger.info(f"Файл загружен: {filename}")

            if new_filenames:
                current_index = len(image_order) + 1
                for filename in new_filenames:
                    redis_client.hset(f'session:{session_id}:images', str(current_index), filename)
                    current_index += 1
                logger.info(f"Обновлен порядок изображений в Redis для сессии: {session_id}")

    return render_template('index.html', images=images, gif_file='animation.gif' if gif_exists else None)


@app.route('/upload', methods=['POST'])
def upload():
    """
    Загружает изображения и сохраняет их имена в Redis.
    """
    session_id = session.get('session_id')
    if not session_id:
        logger.error("Ошибка: Session ID не найден")
        return jsonify(error='Session ID not found'), 400

    files = request.files.getlist('files')
    if not files:
        logger.error("Ошибка: Файлы не загружены")
        return jsonify(error='No files uploaded'), 400

    upload_folder = os.path.join(uploads_root, session_id)
    os.makedirs(upload_folder, exist_ok=True)
    logger.info(f"Папка для загрузок создана: {upload_folder}")

    new_filenames = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            new_filenames.append(filename)
            logger.info(f"Файл сохранен: {filename}")

    image_order = redis_client.hgetall(f'session:{session_id}:images')
    current_index = len(image_order) + 1
    for filename in new_filenames:
        redis_client.hset(f'session:{session_id}:images', str(current_index), filename)
        current_index += 1
    logger.info(f"Порядок изображений обновлен в Redis для сессии: {session_id}")
    logger.info(f'Новые изображения загружены порядок изображений в Redis: {image_order}')

    return jsonify(success=True, filenames=new_filenames)


@app.route('/get_images', methods=['GET'])
def get_images():
    """
    Возвращает список изображений для текущей сессии из Redis.
    """
    logger.info('Получение списка изображений для текущей сессии')
    session_id = session.get('session_id')
    if not session_id:
        logger.error("Ошибка: Session ID не найден")
        return jsonify(error='Session ID not found'), 400

    image_order = redis_client.hgetall(f'session:{session_id}:images')
    if not image_order:
        logger.info(f"Изображения не найдены для сессии: {session_id}")
        return jsonify(images=[])

    decoded_image_order = {key.decode('utf-8'): value.decode('utf-8') for key, value in image_order.items()}
    images = [decoded_image_order[key] for key in sorted(decoded_image_order.keys(), key=int)]
    logger.info(f"Получены изображения для сессии: {session_id}")

    return jsonify(images=images)


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    """
    Обновляет порядок изображений в Redis.
    """
    session_id = session.get('session_id')
    if not session_id:
        logger.error("Ошибка: Session ID не найден")
        return jsonify(error='Session ID not found'), 400

    image_order = request.form.get('image_order')
    if not image_order:
        logger.error("Ошибка: Порядок изображений не предоставлен")
        return jsonify(error='Image order not provided'), 400

    try:
        image_order = json.loads(image_order)
        logger.info(f"Получен порядок изображений: {image_order}")
    except json.JSONDecodeError:
        logger.error("Ошибка: Неверный формат порядка изображений")
        return jsonify(error='Invalid image order format'), 400

    redis_client.delete(f'session:{session_id}:images')
    logger.info(f"Очищен старый порядок изображений для сессии: {session_id}")


@app.route('/remove_image', methods=['POST'])
def remove_image():
    """
    Удаляет изображение из Redis и файловой системы.
    """
    # Получаем session_id из сессии
    session_id = session.get('session_id')
    if not session_id:
        logger.error("Ошибка: Session ID не найден")
        return jsonify(error='Session ID not found'), 400

    # Получаем имя изображения из запроса
    image_name = request.form.get('image_name')
    logger.info(f"Имя изображения: {image_name}")
    if not image_name:
        logger.error("Ошибка: Имя изображения не предоставлено")
        return jsonify(error='Image name not provided'), 400

    logger.info(f"Начало удаления изображения: {image_name} для сессии: {session_id}")

    # Удаляем изображение из Redis
    image_order = redis_client.hgetall(f'session:{session_id}:images')
    logger.info(f"Исходный порядок изображений: {image_order}")
    image_found_in_redis = False

    for index, filename in image_order.items():
        if filename.decode('utf-8') == image_name:
            redis_client.hdel(f'session:{session_id}:images', index)
            logger.info(f"Изображение удалено из Redis: {image_name} (индекс: {index.decode('utf-8')})")
            image_found_in_redis = True
            break

    if not image_found_in_redis:
        logger.warning(f"Изображение не найдено в Redis: {image_name}")

    # Удаляем файл из файловой системы
    file_path = os.path.join(uploads_root, session_id, image_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Файл изображения удален из файловой системы: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла изображения: {e}")
            return jsonify(error='Failed to delete image file'), 500
    else:
        logger.warning(f"Файл изображения не найден в файловой системе: {file_path}")

    logger.info(f"Удаление изображения завершено: {image_name}")
    logger.info(f"Новый порядок изображений: {image_order}")
    return jsonify(success=True)


def clean_uploads():
    """
    Очищает папку uploads при запуске приложения.
    """
    if os.path.exists(uploads_root):
        for item in os.listdir(uploads_root):
            item_path = os.path.join(uploads_root, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    # Todo: Добавить логику генерации gif
    return jsonify(success=True)


@app.route('/get_session_id', methods=['POST'])
def get_session_id():
    """
    Возвращает уникальный идентификатор сессии.
    """
    logger.info('Вызов функции Get session ID')
    session_id = request.headers.get('X-Session-Id')

    if not session_id:
        # Если session_id не передан, создаём новый
        session_id = str(uuid.uuid4())
        logger.info(f'Создан новый Session ID: {session_id}')
    else:
        logger.info(f'Используется существующий Session ID: {session_id}')

    return jsonify(session_id=session_id)


if __name__ == '__main__':
    clean_uploads()
    app.run(debug=True, host='0.0.0.0', port=5000)
