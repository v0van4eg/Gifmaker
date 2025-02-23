import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, json
from flask import send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
import requests
import logging
import shutil
import redis

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Подключение к Redis
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)


# Фильтр допустимых форматов файлов
def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'tiff'))


uploads_root = os.path.join(app.root_path, 'uploads')


# def clean_uploads():
#     if os.path.exists(uploads_root):
#         for item in os.listdir(uploads_root):
#             item_path = os.path.join(uploads_root, item)
#             if os.path.isdir(item_path):
#                 shutil.rmtree(item_path)
#             else:
#                 os.remove(item_path)


@app.route('/get_images', methods=['GET'])
def get_images():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    upload_folder = os.path.join(uploads_root, session_id)
    images = []

    if os.path.exists(upload_folder):
        image_order = redis_client.hgetall(f'session:{session_id}:images')
        if image_order:
            sorted_images = sorted(image_order.items(), key=lambda x: int(x[0]))
            images = [image_name.decode('utf-8') for _, image_name in sorted_images]
        else:
            for f in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, f)
                if os.path.isfile(file_path) and allowed_file(f) and f != 'animation.gif':
                    images.append(f)
    return jsonify(images=images)


@app.route('/get_session_id', methods=['GET'])
def get_session_id():
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    return jsonify(session_id=session_id)


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        upload_folder = os.path.join(uploads_root, session['session_id'])
        os.makedirs(upload_folder, exist_ok=True)

    session_id = session['session_id']
    upload_folder = os.path.join(uploads_root, session_id)
    images = []
    if os.path.exists(upload_folder):
        for f in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, f)
            if os.path.isfile(file_path) and allowed_file(f) and f != 'animation.gif':
                images.append(f)

    gif_file = os.path.join(upload_folder, 'animation.gif')

    if request.method == 'POST':
        files = request.files.getlist('files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                images.append(filename)

    return render_template('index.html', images=images, gif_file=gif_file if os.path.exists(gif_file) else None)


@app.route('/new_session', methods=['GET'])
def new_session():
    """
    Создает новую сессию, удаляя старые данные и файлы.
    """
    session_id = session.get('session_id')
    if session_id:
        # Удаляем данные о сессии из Redis
        redis_client.delete(f'session:{session_id}')

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
    session['session_id'] = new_session_id

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


# @app.route('/uploads/<filename>')
# def get_uploaded_file(filename):
#     session_id = session.get('session_id')
#     if not session_id:
#         return "Session ID not found", 404
#     return send_from_directory(os.path.join(uploads_root, session_id), filename)


@app.route('/upload', methods=['POST'])
def upload():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify(error='No files uploaded'), 400

    upload_url = 'http://api/upload'
    headers = {'X-Session-ID': session_id}
    files_data = [('files', (file.filename, file.stream, file.mimetype)) for file in files]

    response = requests.post(upload_url, files=files_data, headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        new_filenames = response_data.get('filenames', [])
        if isinstance(new_filenames, list):
            for idx, new_filename in enumerate(new_filenames, start=1):
                redis_client.hset(f'session:{session_id}:images', str(idx), new_filename)
            return jsonify(success=True, filenames=new_filenames)
        else:
            return jsonify(error='Unexpected response format from image_processing'), 500
    else:
        return jsonify(error='Failed to upload files'), response.status_code


@app.route('/remove_image', methods=['POST'])
def remove_image():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'message': 'Session ID not found'}), 400

    image_name = request.form.get('image_name')
    if not image_name:
        return jsonify({'success': False, 'message': 'Image name not specified'}), 400

    redis_client.hdel(f'session:{session_id}:images', image_name)

    response = requests.post(f'http://api/remove_image',
                             headers={'X-Session-ID': session_id},
                             data={'image_name': image_name})

    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify({'success': False, 'message': response.text}), response.status_code


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(success=False, error='Session ID not found'), 400

    image_order = request.form.get('image_order')
    if not image_order:
        return jsonify(success=False, error='Image order not provided'), 400

    image_order_dict = json.loads(image_order)
    redis_client.hmset(f'session:{session_id}:images', image_order_dict)

    reorder_url = 'http://api/reorder_images'
    response = requests.post(reorder_url,
                             headers={'X-Session-ID': session_id},
                             data={'image_order': json.dumps(image_order_dict)})

    if response.status_code == 200:
        return jsonify(success=True)
    else:
        return jsonify(success=False, error='Failed to reorder images'), response.status_code


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
    images_json = redis_client.hget(f'session:{session_id}', 'images')
    if not images_json:
        logger.error("No image order found in Redis for session: %s", session_id)
        return jsonify(error='No image order found'), 400

    image_order = json.loads(images_json)

    # Подготавливаем данные для отправки в микросервис gif_generator
    generate_url = 'http://api/generate_gif'
    headers = {'X-Session-ID': session_id}
    data = {
        'duration': duration,
        'loop': loop,
        'resize': resize,
        'image_order': json.dumps(image_order)  # Передаем порядок изображений
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


if __name__ == '__main__':
    clean_uploads()
    app.run(debug=True, host='0.0.0.0', port=5000)
