from flask import Flask, request, jsonify, session, render_template
from flask import send_from_directory
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Фильтр допустимых форматов файлов
def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'tiff'))


uploads_root = os.path.join(app.root_path, 'uploads')


@app.route('/uploads/<path:filename>')
def get_uploaded_file(filename):
    """
    Возвращает файл из папки загрузок.
    """
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 404

    upload_folder = os.path.join(uploads_root, session_id)
    return send_from_directory(upload_folder, filename)


@app.route('/new_session', methods=['GET'])
def new_session():
    """
    Создает новую сессию, удаляя старые данные и файлы.
    """
    session_id = session.get('session_id')
    if session_id:
        # Удаляем данные о сессии из Redis
        redis_client.delete(f'session:{session_id}:images')

        # Удаляем папку с файлами, связанными с сессией
        session_folder = os.path.join(uploads_root, session_id)
        if os.path.exists(session_folder):
            try:
                shutil.rmtree(session_folder)  # Рекурсивно удаляем папку
                logger.info(f'Папка сессии удалена: {session_folder}')
            except Exception as e:
                logger.error(f'Ошибка при удалении папки сессии: {e}')
                return jsonify(error='Failed to delete session folder'), 500

    # Генерируем новый session_id
    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id  # Сохраняем session_id в сессии Flask

    # Создаем новую папку для загрузок
    upload_folder = os.path.join(uploads_root, new_session_id)
    try:
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f'Создана новая папка для загрузок: {upload_folder}')
    except Exception as e:
        logger.error(f'Ошибка при создании папки для загрузок: {e}')
        return jsonify(error='Failed to create upload directory'), 500

    # Возвращаем новый session_id
    return jsonify(session_id=new_session_id)


@app.route('/get_session_id', methods=['GET'])
def get_session_id():
    """
    Генерирует новый session_id и сохраняет его в сессии Flask.
    """
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id  # Сохраняем session_id в сессии Flask

    # Возвращаем session_id
    return jsonify(session_id=session_id)


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Главная страница приложения.
    Отображает загруженные изображения и форму для создания GIF.
    """
    # Проверяем, есть ли session_id в сессии Flask
    session_id = session.get('session_id')
    if not session_id:
        # Создаем новую сессию, если session_id отсутствует
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id

        # Создаем папку для загрузки файлов
        upload_folder = os.path.join(uploads_root, session_id)
        try:
            os.makedirs(upload_folder, exist_ok=True)
            logger.info(f'Создана папка для загрузок: {upload_folder}')
        except Exception as e:
            logger.error(f'Ошибка при создании папки для загрузок: {e}')
            return jsonify(error='Failed to create upload directory'), 500

    # Получаем список изображений из Redis
    image_order = redis_client.hgetall(f'session:{session_id}:images')
    if image_order:
        # Декодируем ключи и значения из bytes в строки
        decoded_image_order = {key.decode('utf-8'): value.decode('utf-8') for key, value in image_order.items()}
        images = [decoded_image_order[key] for key in sorted(decoded_image_order.keys(), key=int)]
    else:
        images = []

    # Получаем путь к GIF-файлу, если он существует
    gif_file = os.path.join(uploads_root, session_id, 'animation.gif')
    gif_exists = os.path.exists(gif_file)

    # Обработка загрузки файлов (если запрос POST)
    if request.method == 'POST':
        files = request.files.getlist('files')
        if files:
            # Сохраняем файлы и обновляем порядок изображений в Redis
            new_filenames = []
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(uploads_root, session_id, filename)
                    file.save(file_path)
                    new_filenames.append(filename)

            # Обновляем порядок изображений в Redis
            if new_filenames:
                current_index = len(image_order) + 1
                for filename in new_filenames:
                    redis_client.hset(f'session:{session_id}:images', str(current_index), filename)
                    current_index += 1

                # Обновляем список изображений
                image_order = redis_client.hgetall(f'session:{session_id}:images')
                decoded_image_order = {key.decode('utf-8'): value.decode('utf-8') for key, value in image_order.items()}
                images = [decoded_image_order[key] for key in sorted(decoded_image_order.keys(), key=int)]

    # Отображаем шаблон с данными
    return render_template('index.html', images=images, gif_file='animation.gif' if gif_exists else None)


@app.route('/upload', methods=['POST'])
def upload():
    """
    Загружает изображения и сохраняет их имена в Redis.
    """
    logger.info("Начало обработки запроса на загрузку файлов.")

    session_id = session.get('session_id')
    if not session_id:
        logger.error("Session ID не найден в сессии.")
        return jsonify(error='Session ID not found'), 400

    logger.debug(f"Session ID: {session_id}")

    files = request.files.getlist('files')
    if not files:
        logger.error("Файлы для загрузки не предоставлены.")
        return jsonify(error='No files uploaded'), 400

    logger.debug(f"Получено файлов: {len(files)}")

    # Получаем текущий порядок изображений из Redis
    image_order = redis_client.hgetall(f'session:{session_id}:images')
    logger.debug(f"Текущий порядок изображений в Redis: {image_order}")

    # Создаем папку для загрузок, если она не существует
    upload_folder = os.path.join(uploads_root, session_id)
    os.makedirs(upload_folder, exist_ok=True)
    logger.debug(f"Папка для загрузок: {upload_folder}")

    # Добавляем новые изображения
    new_filenames = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            new_filenames.append(filename)
            logger.debug(f"Файл {filename} успешно сохранен в {file_path}")
        else:
            logger.warning(f"Файл {file.filename} не был загружен, так как он не разрешен или отсутствует.")

    logger.debug(f"Новые файлы, добавленные в сессию: {new_filenames}")

    # Обновляем порядок изображений в Redis
    current_index = len(image_order) + 1
    for filename in new_filenames:
        redis_client.hset(f'session:{session_id}:images', str(current_index), filename)
        logger.debug(f"Добавлено изображение {filename} в Redis с индексом {current_index}")
        current_index += 1

    logger.info("Загрузка файлов завершена успешно.")
    return jsonify(success=True, filenames=new_filenames)


@app.route('/get_images', methods=['GET'])
def get_images():
    """
    Возвращает список изображений для текущей сессии из Redis.
    """
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    # Получаем порядок изображений из Redis
    image_order = redis_client.hgetall(f'session:{session_id}:images')
    if not image_order:
        return jsonify(images=[])

    # Декодируем ключи и значения из bytes в строки
    decoded_image_order = {key.decode('utf-8'): value.decode('utf-8') for key, value in image_order.items()}
    images = [decoded_image_order[key] for key in sorted(decoded_image_order.keys(), key=int)]

    return jsonify(images=images)


@app.route('/remove_image', methods=['POST'])
def remove_image():
    """
    Удаляет изображение из Redis.
    """
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    image_name = request.form.get('image_name')
    if not image_name:
        return jsonify(error='Image name not provided'), 400

    # Получаем текущий порядок изображений из Redis
    image_order = redis_client.hgetall(f'session:{session_id}:images')
    if not image_order:
        return jsonify(error='No images found'), 400

    # Удаляем изображение из Redis
    for key, value in image_order.items():
        if value.decode('utf-8') == image_name:
            redis_client.hdel(f'session:{session_id}:images', key)
            break

    return jsonify(success=True)


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    """
    Изменяет порядок изображений в Redis.
    """
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    image_order_json = request.form.get('image_order')
    if not image_order_json:
        return jsonify(error='Image order not provided'), 400

    # Обновляем порядок изображений в Redis
    image_order = json.loads(image_order_json)
    redis_client.hmset(f'session:{session_id}:images', image_order)

    return jsonify(success=True)


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    """
    Генерирует GIF на основе данных из Redis.
    """
    # Получаем session_id из сессии Flask
    session_id = session.get('session_id')
    if not session_id:
        logger.error("Session ID not found in generate_gif.")
        return jsonify(error='Session ID not found'), 400

    # Получаем параметры для генерации GIF из запроса
    duration = request.form.get('duration', 300)
    loop = request.form.get('loop', 0)
    resize = request.form.get('resize')

    # Получаем порядок изображений из Redis
    image_order = redis_client.hgetall(f'session:{session_id}:images')
    if not image_order:
        logger.error("No image order found in Redis for session: %s", session_id)
        return jsonify(error='No image order found'), 400

    # Декодируем ключи и значения из bytes в строки
    decoded_image_order = {key.decode('utf-8'): value.decode('utf-8') for key, value in image_order.items()}

    # Подготавливаем данные для отправки в микросервис gif_generator
    generate_url = 'http://gif_generator:5002/generate_gif'
    headers = {'X-Session-ID': session_id}
    data = {
        'duration': duration,
        'loop': loop,
        'resize': resize,
        'image_order': json.dumps(decoded_image_order)  # Передаем порядок изображений
    }

    # Отправляем запрос в микросервис gif_generator
    try:
        response = requests.post(generate_url, headers=headers, data=data)
        response.raise_for_status()  # Проверяем статус ответа

        response_data = response.json()
        gif_url = response_data.get('gif_url')
        if gif_url:
            logger.info("GIF успешно сгенерирован: %s", gif_url)
            return jsonify(success=True, gif_url=gif_url)
        else:
            logger.error("GIF URL не найден в ответе от микросервиса gif_generator.")
            return jsonify(success=False, error='GIF URL not found in response'), 500

    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при генерации GIF: %s", str(e))
        return jsonify(error='Failed to generate GIF'), 500


def clean_uploads():
    if os.path.exists(uploads_root):
        for item in os.listdir(uploads_root):
            item_path = os.path.join(uploads_root, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)


if __name__ == '__main__':
    clean_uploads()
    app.run(debug=True, host='0.0.0.0', port=5000)
