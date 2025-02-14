# web_ui/main.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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


@app.route('/', methods=['GET', 'POST'])
def index():
    # clean_uploads()
    logger.info('Переход на главную страницу...')
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    logger.info(f'Создаём новую сессию session_id={session_id}')
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
    # session_id = session.get('session_id')
    session_id = request.form.get('session_id')
    logger.info(f'Создание новой сессии...session_id={session_id}')
    # Очистка файлов при старте (без удаления папок)
    clean_uploads()
    if session_id:
        session.pop('images', None)
        session['session_id'] = str(uuid.uuid4())
    return redirect(url_for('index'))


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    session_id = session.get('session_id')
    logger.info('@@@ Выбран маршрут Создание GIF...')
    if not session_id:
        return redirect(url_for('index'))
    duration = request.form.get('duration', 100)
    loop = request.form.get('loop', 0)
    resize = request.form.get('resize')
    generate_url = 'http://gif_generator:5004/generate_gif'
    response = requests.post(generate_url, data={
        'session_id': session_id,
        'duration': duration,
        'loop': loop,
        'resize': resize
    })
    if response.status_code == 200:
        return redirect(url_for('index'))
    else:
        logger.error(f'Ошибка при создании GIF: {response.text}')
        return jsonify(error='Failed to generate GIF'), 500


@app.route('/upload', methods=['POST'])
def upload():
    logger.info(f"@@@ Вызываем загрузку. В обработчике Session ID in web_ui: {session_id}")
    session_id = session.get('session_id')
    logger.info(f"@@@ В обработчике Session ID in web_ui: {session_id}")
    files = request.files.getlist('files')
    if not files:
        return redirect(url_for('index'))
    upload_url = 'http://file_service:5002/upload'
    data = {'session_id': session_id}
    files_data = [('files', (file.filename, file.stream, file.mimetype)) for file in files]
    response = requests.post(upload_url, data=data, files=files_data)
    if response.status_code == 200:
        response_data = response.json()
        new_filenames = response_data.get('filenames', [])
        session.setdefault('images', []).extend(new_filenames)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
