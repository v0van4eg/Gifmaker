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
logging.basicConfig(
    level=logging.DEBUG,  # Устанавливаем уровень логирования на DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат логов
    handlers=[
        logging.StreamHandler()  # Вывод логов в консоль
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для подписи сессии
uploads_root = os.path.join(app.root_path, 'uploads')  # Путь к директории загрузок

# Подключение к Redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

logger.debug("Подключение к Redis установлено.")


# Фильтр допустимых форматов файлов
def allowed_file(filename):
    """
    Проверяет, является ли файл допустимого типа.
    """
    logger.debug(f"Проверка допустимости файла: {filename}")
    is_allowed = filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'tiff'))
    logger.debug(f"Файл {filename} допустим: {is_allowed}")
    return is_allowed


def clean_uploads():
    """
    Очищает директорию загрузок.
    Удаляет все файлы и папки в директории uploads при старте приложения.
    """
    logger.info("Проверка наличия директории загрузок...")
    if os.path.exists(uploads_root):
        logger.info("Очистка старых загрузок...")
        for item in os.listdir(uploads_root):
            item_path = os.path.join(uploads_root, item)
            if os.path.isdir(item_path):
                logger.debug(f"Удаление директории: {item_path}")
                shutil.rmtree(item_path)  # Рекурсивно удаляем директорию и её содержимое
            else:
                logger.debug(f"Удаление файла: {item_path}")
                os.remove(item_path)  # Удаляем файл
    else:
        logger.info("Директория загрузок не найдена, очистка не требуется.")


@app.route('/get_session_id', methods=['GET'])
def get_session_id():
    """Создает или возвращает session_id."""
    logger.debug("Запрос на получение session_id.")
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f"Создан новый session_id: {session['session_id']}")
    logger.debug(f"Возвращаем session_id: {session['session_id']}")
    return jsonify(session_id=session['session_id'])


@app.route('/get_order', methods=['GET'])
def get_order():
    """Возвращает текущий порядок изображений из Redis."""
    logger.debug("Запрос на получение порядка изображений.")
    session_id = request.headers.get('X-Session-ID', session.get('session_id'))
    if not session_id:
        return jsonify(error='Session ID not found'), 400
    logger.info(f'Текущий session_id: {session_id}')
    # Получаем порядок файлов из Redis
    redis_key = f"session:{session_id}:order"
    if redis_client.exists(redis_key):
        current_order = redis_client.lrange(redis_key, 0, -1)
        current_order = [item.decode('utf-8') for item in current_order]
        logger.info(f"Возвращаю текущий порядок изображений:")
        for item in current_order:
            logger.info(f"Файл - {item}")

        return jsonify(order=current_order)
    else:
        return jsonify(order=[])


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Главная страница приложения.
    Отображает загруженные изображения и форму для создания GIF.
    """
    logger.info("Запрос на главную страницу.")

    # Проверяем, есть ли session_id
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f"Создан новый session_id: {session['session_id']}")

    session_id = session['session_id']
    logger.debug(f"Используется session_id: {session_id}")

    upload_folder = os.path.join(uploads_root, session_id)
    if not os.path.exists(upload_folder):
        try:
            os.makedirs(upload_folder, exist_ok=True)
            logger.info(f"Папка для загрузки создана: {upload_folder}")
        except Exception as e:
            logger.error(f"Ошибка при создании папки: {e}")
            return jsonify(error='Failed to create upload directory'), 500

    # Получаем список загруженных файлов из Redis
    redis_key = f"session:{session_id}:order"
    if redis_client.exists(redis_key):
        order = redis_client.lrange(redis_key, 0, -1)
        order = [item.decode('utf-8') for item in order]
    else:
        order = []

    logger.info(f"Загруженные изображения: {order}")

    gif_file = os.path.join(upload_folder, 'animation.gif')

    return render_template(
        'index.html',
        session_id=session_id,  # Добавляем session_id для корректных ссылок
        images=order,
        gif_file=gif_file if os.path.exists(gif_file) else None
    )


@app.route('/new_session', methods=['GET'])
def new_session():
    """
    Создает новую сессию и очищает старые данные.
    """
    logger.info("Запрос на создание новой сессии.")
    session_id = session.get('session_id')
    if session_id:
        session_folder = os.path.join(uploads_root, session_id)
        if os.path.exists(session_folder):
            logger.info(f"Удаление папки сессии: {session_folder}")
            shutil.rmtree(session_folder)  # Полностью удаляем папку сессии

    # Удаляем сессионные данные
    session.pop('session_id', None)
    session.pop('order', None)

    # Генерируем новый session_id
    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id
    logger.info(f"Создан новый session_id: {new_session_id}")

    # Создаем папку для загрузки
    upload_folder = os.path.join(uploads_root, new_session_id)
    try:
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f"Папка для загрузки создана: {upload_folder}")
    except Exception as e:
        logger.error(f"Ошибка при создании папки: {e}")
        return jsonify(error='Failed to create upload directory'), 500

    return redirect(url_for('index'))


# @app.route('/uploads/<path:filename>', methods=['GET'])
# def get_uploaded_file(session_id, filename):
#     session_path = os.path.join(uploads_root, session_id)
#     return send_from_directory(session_path, filename)


@app.route('/upload', methods=['POST'])
def upload():
    """
    Обрабатывает загрузку изображений.
    """
    logger.info("Запрос на загрузку изображений.")
    session_id = session.get('session_id')

    logger.info(f"Session ID: {session_id}")
    files = request.files.getlist('files')
    if not files:
        logger.error("Нет загруженных файлов.")
        return jsonify(error='No files uploaded'), 400

    # Подготавливаем данные для отправки в микросервис srv_upload
    upload_url = 'http://upload:5001/upload'
    headers = {'X-Session-ID': session_id}
    files_data = [('files', (file.filename, file.stream, file.mimetype)) for file in files]

    try:
        logger.debug(f"Отправка запроса в микросервис srv_upload: {upload_url}")
        response = requests.post(upload_url, files=files_data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            new_filenames = response_data.get('filenames', [])
            if isinstance(new_filenames, list):
                logger.info(f"Новые имена файлов добавлены в Redis: {new_filenames}")
                return jsonify(success=True, filenames=new_filenames)
            else:
                logger.error(f"Ошибка: 'filenames' не является списком. Получено: {new_filenames}")
                return jsonify(error='Unexpected response format from srv_upload'), 500
        else:
            logger.error(f"Ошибка при загрузке файлов: {response.text}")
            return jsonify(error='Failed to upload files'), response.status_code
    except Exception as e:
        logger.error(f"Ошибка при отправке запроса в srv_upload: {str(e)}")
        return jsonify(error='Internal server error'), 500


@app.route('/remove_image', methods=['POST'])
def remove_image():
    """
    Удаляет изображение из Redis и с диска.
    """
    logger.info("Запрос на удаление изображения.")

    # Получаем Session ID
    session_id = session['session_id']
    # session_id = request.headers.get('X-Session-ID')
    if not session_id:
        logger.error("Session ID не найден в заголовках")
        return jsonify({'success': False, 'message': 'Session ID not found'}), 400

    logger.info(f"Session ID: {session_id}")
    redis_key = f"session:{session_id}:order"

    # Проверяем наличие записи в Redis
    if redis_client.exists(redis_key):
        image_name = request.form.get('image_name')
        if not image_name:
            logger.error("Имя изображения не указано!!!!!!!.")
            return jsonify({'success': False, 'message': 'Image name not specified'}), 400

        # Удаляем изображение из списка в Redis
        redis_client.lrem(redis_key, 0, image_name)
        logger.info(f"Изображение {image_name} удалено из Redis.!!!!!!!!!111")

        # Формируем путь к файлу и пытаемся его удалить с диска
        file_path = os.path.join(uploads_root, session_id, image_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Файл {file_path} успешно удален с диска.")
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {file_path}: {str(e)}")
                return jsonify({'success': False, 'message': 'Error deleting file from disk'}), 500
        else:
            logger.warning(f"Файл {file_path} не найден на диске.")
    else:
        logger.error("Session ID не найден ")
        return jsonify({'success': False, 'message': 'Session ID not found'}), 400

    # Вызавть новый порядок из get_order
    order = get_order()
    logger.info(f'Новый порядок изображений: {order}')
    return jsonify({'success': True})


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    logger.info("Запрос на изменение порядка изображений.")

    session_id = session['session_id']
    if not session_id:
        return jsonify({'success': False, 'message': 'Session ID not found'}), 400

    redis_key = f"session:{session_id}:order"
    if not redis_client.exists(redis_key):
        return jsonify({'success': False, 'message': 'No images found for session'}), 400

    # Читаем новый порядок изображений
    image_order_json = request.form.get('image_order')
    if not image_order_json:
        return jsonify({'success': False, 'message': 'No image order provided'}), 400

    try:
        new_order = json.loads(image_order_json)
        new_order = [new_order[key] for key in sorted(new_order.keys(), key=int)]
    except Exception as e:
        logger.error(f"Ошибка при обработке порядка изображений: {str(e)}")
        return jsonify({'success': False, 'message': 'Invalid image order format'}), 400

    # Обновляем порядок файлов в Redis
    redis_client.delete(redis_key)
    redis_client.rpush(redis_key, *new_order)

    logger.info(f"Новый порядок сохранен в Redis: {new_order}")
    return jsonify({'success': True, 'new_order': new_order})

    # TODO: Улучшить логирование


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    redis_key = f"session:{session_id}:order"
    if redis_client.exists(redis_key):
        order = redis_client.lrange(redis_key, 0, -1)
        order = [item.decode('utf-8') for item in order]
        logger.info(f"Передаём порядок изображений: {order}")
        # Здесь можно использовать order для генерации GIF
        # TODO: Дописать роут /generate_gif


@app.route('/uploads/<session_id>/<path:filename>')
def get_uploaded_file(session_id, filename):
    session_id = session.get('session_id')
    # session_id = request.headers.get('X-Session-ID')
    logger.debug(f'Returning file {filename} from session {session_id}')
    return send_from_directory(os.path.join(uploads_root, session_id), filename)


if __name__ == '__main__':
    clean_uploads()  # Очищаем директорию загрузок при запуске приложения
    redis_client.flushdb()  # Очистка Redis перед запуском
    logger.info("Запуск Flask-приложения на порту 5000.")
    app.run(debug=True, host='0.0.0.0', port=5000)
