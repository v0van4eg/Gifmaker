# web_ui/main.py

from flask import *
import os
from werkzeug.utils import secure_filename
import requests
import logging
import shutil
import redis
import uuid
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)  # Установка уровня логирования в DEBUG для более подробного логирования
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для подписи сессии
uploads_root = os.path.join(app.root_path, 'uploads')  # Путь к директории загрузок


# Фильтр допустимых форматов файлов
def allowed_file(filename):
    """
    Проверяет, является ли файл допустимого типа.

    Входные параметры:
    - filename: Имя файла

    Возвращает:
    - True, если файл допустимого типа, иначе False
    """
    logger.debug(f"Checking if file {filename} is allowed.")
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'tiff'))


def clean_uploads():
    """
    Очищает директорию загрузок.
    Удаляет все файлы и папки в директории uploads при старте приложения.
    """
    logger.info('Checking for uploads directory...')
    if os.path.exists(uploads_root):
        logger.info('Cleaning old uploads...')
        for item in os.listdir(uploads_root):
            item_path = os.path.join(uploads_root, item)
            if os.path.isdir(item_path):
                logger.debug(f"Removing directory: {item_path}")
                shutil.rmtree(item_path)  # Рекурсивно удаляем директорию и её содержимое
            else:
                logger.debug(f"Removing file: {item_path}")
                os.remove(item_path)  # Удаляем файл


# Подключение к Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)


@app.route('/get_session_id', methods=['GET'])
def get_session_id():
    """Создает или возвращает session_id."""
    if 'session_id' not in session:
        logger.debug(f'No session_id in session')
        session['session_id'] = str(uuid.uuid4())
        logger.info(f'Создан новый session_id: {session["session_id"]}')
    logger.debug(f'Возвращаем session_id: {session["session_id"]}')
    return jsonify(session_id=session['session_id'])


@app.route('/update_order', methods=['POST'])
def update_order():
    logger.info('Обновление порядка изображений')
    """Обновляет порядок изображений в Redis."""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 400
    logger.info(f'Session ID; {session_id}')
    new_order = request.json.get('order')
    logger.info(f'New order: {new_order}')
    if not new_order:
        logger.info('No new order provided')
        return jsonify(error='No order provided'), 400

    # Сохраняем порядок в Redis
    redis_key = f"session:{session_id}:order"
    redis_client.delete(redis_key)  # Очищаем старый порядок
    redis_client.rpush(redis_key, *new_order)  # Добавляем новый порядок

    return jsonify(success=True)


@app.route('/get_order', methods=['GET'])
def get_order():
    """Возвращает текущий порядок изображений из Redis."""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    # Получаем порядок из Redis
    redis_key = f"session:{session_id}:order"
    current_order = redis_client.lrange(redis_key, 0, -1)
    current_order = [item.decode('utf-8') for item in current_order]

    return jsonify(order=current_order)


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Главная страница приложения.
    Отображает загруженные изображения и форму для создания GIF.
    Возвращает:
    - HTML шаблон с загруженными изображениями и параметрами для создания GIF
    """
    logger.info('Transition to the home page...')
    # Проверяем, есть ли session_id в сессии
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f'Created new session session_id={session["session_id"]}')

        # Создаем папку для загрузки только при инициализации новой сессии
        upload_folder = os.path.join(uploads_root, session['session_id'])
        if not os.path.exists(upload_folder):
            try:
                os.makedirs(upload_folder, exist_ok=True)
                logger.info(f'Folder successfully created: {upload_folder}')
            except Exception as e:
                logger.error(f'Error creating folder: {e}')
                return jsonify(error='Failed to create upload directory'), 500

    session_id = session['session_id']
    logger.debug(f'Using existing session_id={session_id}')

    # Получаем список изображений из папки загрузки
    upload_folder = os.path.join(uploads_root, session_id)
    images = []
    if os.path.exists(upload_folder):
        for f in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, f)
            if os.path.isfile(file_path) and allowed_file(f) and f != 'animation.gif':
                images.append(f)
                logger.debug(f'Loaded image: {f}')

    gif_file = os.path.join(upload_folder, 'animation.gif')

    if request.method == 'POST':
        files = request.files.getlist('files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)  # Безопасное имя файла
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                logger.debug(f'File {filename} saved to {file_path}')
                images.append(filename)

    return render_template('index.html', images=images, gif_file=gif_file if os.path.exists(gif_file) else None)


@app.route('/new_session', methods=['GET'])
def new_session():
    """
    Создает новую сессию и очищает старые данные.
    Возвращает:
    - Перенаправление на главную страницу
    """
    session_id = session.get('session_id')
    logger.info(f'Cleaning session... Current session_id={session_id}')

    if session_id:
        session_folder = os.path.join(uploads_root, session_id)
        if os.path.exists(session_folder):
            logger.info(f'Removing session folder: {session_folder}')
            shutil.rmtree(session_folder)  # Полностью удаляем папку сессии

    # Удаляем сессионные данные
    session.pop('session_id', None)
    session.pop('order', None)

    # Генерируем новый session_id
    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id
    logger.info(f'Created new session_id={new_session_id}')
    logger.info('Creating folder for uploads...')
    upload_folder = os.path.join(uploads_root, new_session_id)
    try:
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f'Folder successfully created: {upload_folder}')
    except Exception as e:
        logger.error(f'Error creating folder: {e}')
        return jsonify(error='Failed to create upload directory'), 500

    return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def get_uploaded_file(filename):
    """
    Возвращает загруженный файл.
    Входные параметры:
    - filename: Имя файла
    Возвращает:
    - Загруженный файл или сообщение об ошибке
    """
    session_id = session.get('session_id')
    if not session_id:
        logger.error("Session ID not found in get_uploaded_file.")
        return "Session ID not found", 404
    logger.debug(f'Returning file {filename} from session {session_id}')
    return send_from_directory(os.path.join(uploads_root, session_id), filename)


@app.route('/upload', methods=['POST'])
def upload():
    """
    Обрабатывает загрузку изображений.
    Входные параметры:
    - files: Файлы для загрузки
    Возвращает:
    - JSON с именами новых файлов или сообщение об ошибке
    """
    logger.info("@@@ Вызываем маршрут /upload")

    # Получаем session_id из сессии
    session_id = session.get('session_id')
    if not session_id:
        logger.error("Session ID не найден")
        return jsonify(error='Session ID не найден'), 400
    logger.info(f'Session ID: {session_id}')
    # TODO: Дописать роут /upload


@app.route('/remove_image', methods=['POST'])
def remove_image():
    """
    Удаляет изображение.
    Входные параметры:
    - image_name: Имя файла для удаления
    Возвращает:
    - JSON с успешным статусом или сообщением об ошибке
    """
    session_id = request.headers.get('X-Session-ID')
    logger.info(f"@@@ Route Remove Image. Sending Session ID from web_ui: {session_id}")

    # TODO: Дописать роут /remove_image

@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    logger.info("ЗАГЛУШКА!!!!! Вызываем маршрут /reorder_images")
    return jsonify({'success': True})
    # TODO: Дописать роут /reorder_images


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    logger.info("ЗАГЛУШКА!!!!! Вызываем маршрут /generate_gif")
    return jsonify({'success': True})
    # TODO: Дописать роут /generate_gif


if __name__ == '__main__':
    clean_uploads()  # Очищаем директорию загрузок при запуске приложения
    app.run(debug=True, host='0.0.0.0', port=5000)  # Запускаем Flask-приложение
