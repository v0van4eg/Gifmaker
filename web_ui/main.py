# web_ui/main.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask import send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
import requests
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Фильтр допустимых форматов
def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))


uploads_root = os.path.join(app.root_path, 'uploads')


def clean_uploads():
    # Очистка файлов при старте (включая удаление папок)
    logger.info('Проверяем наличие папки uploads...')
    if os.path.exists(uploads_root):
        logger.info('Очищаем старые загрузки...')

        # Проверяем, является ли uploads_root символической ссылкой
        if os.path.islink(uploads_root):
            logger.info(f'{uploads_root} является символической ссылкой.')
            # Получаем реальный путь, на который указывает ссылка
            real_path = os.path.realpath(uploads_root)
            logger.info(f'Реальный путь: {real_path}')

            # Очищаем содержимое реального каталога
            for item in os.listdir(real_path):
                item_path = os.path.join(real_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)  # Рекурсивно удаляем директорию и её содержимое
                else:
                    os.remove(item_path)  # Удаляем файл
        else:
            # Если это не символическая ссылка, обрабатываем как обычный каталог
            for item in os.listdir(uploads_root):
                item_path = os.path.join(uploads_root, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)  # Рекурсивно удаляем директорию и её содержимое
                else:
                    os.remove(item_path)  # Удаляем файл


clean_uploads()


@app.route('/get_session_id', methods=['GET'])
def get_session_id():
    logger.info("Генерируем session_id")
    session_id = session.get('session_id')
    logger.info(f'Отдаём session_id={session_id}')  # Логируем перед возвратом
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        logger.info(f'Создаём новую сессию session_id={session_id}')
    return jsonify(session_id=session_id)


@app.route('/', methods=['GET', 'POST'])
def index():
    # clean_uploads()
    logger.info('Переход на главную страницу...')
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    logger.info(f'Получем session_id={session_id}')
    upload_folder = os.path.join(uploads_root, session_id)
    logger.info(f'Создаём папку upload_folder={upload_folder}')
    os.makedirs(upload_folder, exist_ok=True)
    images = session.get('images', [])
    gif_file = os.path.join(upload_folder, 'animation.gif')

    if request.method == 'POST':
        files = request.files.getlist('files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)  # Безопасное имя файла
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                session.setdefault('images', []).append(filename)

    return render_template('index.html', images=images, gif_file=gif_file if os.path.exists(gif_file) else None)


@app.route('/new_session', methods=['GET'])
def new_session():
    session_id = session.get('session_id')
    logger.info(f'Очистка сессии... Текущий session_id={session_id}')

    if session_id:
        session_folder = os.path.join(uploads_root, session_id)
        if os.path.exists(session_folder):
            logger.info(f'Удаляем папку сессии: {session_folder}')
            shutil.rmtree(session_folder)  # Полностью удаляем папку сессии

    # Удаляем сессионные данные
    session.pop('session_id', None)
    session.pop('images', None)

    # Генерируем новый session_id
    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id
    logger.info(f'Создан новый session_id={new_session_id}')

    return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def get_uploaded_file(filename):
    session_id = session.get('session_id')
    if not session_id:
        return "Session ID not found", 404
    return send_from_directory(os.path.join(uploads_root, session_id), filename)


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    session_id = session.get('session_id')
    logger.info('@@@ Выбран маршрут Создание GIF...')
    logger.info("Отправляем данные на гиф-генератор")
    if not session_id:
        return redirect(url_for('index'))
    logger.info(f'session_id={session_id}')
    duration = request.form.get('duration', 300)
    logger.info(f'duration={duration}')
    loop = request.form.get('loop', 0)
    logger.info(f'loop={loop}')
    resize = request.form.get('resize')
    logger.info(f'resize={resize}')
    generate_url = 'http://gif_generator:5002/generate_gif'
    response = requests.post(generate_url, data={
        'session_id': session_id,
        'duration': duration,
        'loop': loop,
        'resize': resize
    })
    print(response.status_code)
    if response.status_code == 200:
        return redirect(url_for('index'))
    else:
        logger.error(f'Ошибка при создании GIF: {response.text}')
        return jsonify(error='Failed to generate GIF'), 500


@app.route('/upload', methods=['POST'])
def upload():
    session_id = session.get('session_id')
    logger.info(f"@@@ Маршрут Upload. Session ID in web_ui: {session_id}")
    files = request.files.getlist('files')
    if not files:
        return redirect(url_for('index'))
    upload_url = 'http://image_processing:5001/upload'
    data = {'session_id': session_id}
    files_data = [('files', (file.filename, file.stream, file.mimetype)) for file in files]
    response = requests.post(upload_url, data=data, files=files_data)
    if response.status_code == 200:
        response_data = response.json()
        new_filenames = response_data.get('filenames', [])
        session.setdefault('images', []).extend(new_filenames)
    return redirect(url_for('index'))


# маршруты для манипуляций с файлами
@app.route('/remove_image', methods=['POST'])
def remove_image():
    session_id = session.get('session_id')
    logger.info(f"@@@ Маршрут Remove Image. Session ID in web_ui: {session_id}")
    try:
        image_name = request.form.get('image_name')
        if not image_name:
            return jsonify({'success': False, 'message': 'Имя файла не указано'}), 400

        # Отправляем запрос к микросервису image_processing
        response = requests.post(f'http://image_processing:5001/remove_image',
                                 data={'session_id': session_id, 'image_name': image_name})

        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({'success': False, 'message': response.text}), response.status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify(success=False, error='Session ID not found'), 400

    image_order = request.form.get('image_order')
    logger.info(f'Получен image_order!!!!!!!!!!: {image_order}')

    if not image_order:
        return jsonify(success=False, error='Image order not provided'), 400

    # Логирование для отладки
    logger.info(f'Received image_order: {image_order}')

    # Преобразуем строку image_order в список
    image_order_list = image_order.split(',')

    # Отправляем запрос в image_processing для изменения порядка изображений
    reorder_url = 'http://image_processing:5001/reorder_images'
    logger.info(f'Отправляем image_order: {image_order}')

    response = requests.post(reorder_url, data={
        'session_id': session_id,
        'image_order': ','.join(image_order_list)  # Убедимся, что передаем строку
    })

    if response.status_code == 200:
        # Обновляем порядок изображений в сессии
        session['images'] = image_order_list
        return jsonify(success=True)
    else:
        logger.error(f'Error reordering images: {response.text}')
        return jsonify(success=False, error='Failed to reorder images'), response.status_code


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
