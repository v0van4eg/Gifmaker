# web_ui/main.py
import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, json
from flask import send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
import requests
import logging
import shutil
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Фильтр допустимых форматов
def allowed_file(filename):
    """
    Проверяет, является ли файл допустимого типа.
    Входные параметры:
    - filename: Имя файла
    Возвращает:
    - True, если файл допустимого типа, иначе False
    """
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'tiff'))


uploads_root = os.path.join(app.root_path, 'uploads')


def clean_uploads():
    """
    Очищает директорию загрузок.
    Очистка файлов при старте (включая удаление папок)
    """
    logger.info('Проверяем наличие папки uploads...')
    if os.path.exists(uploads_root):
        logger.info('Очищаем старые загрузки...')
        for item in os.listdir(uploads_root):
            item_path = os.path.join(uploads_root, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)  # Рекурсивно удаляем директорию и её содержимое
            else:
                os.remove(item_path)  # Удаляем файл


@app.route('/get_images', methods=['GET'])
def get_images():
    session_id = request.headers.
    logger.info(f'Получаем список изображений из сессии: {session_id}')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    upload_folder = os.path.join(uploads_root, session_id)

    images = []

    if os.path.exists(upload_folder):
        # Получаем сохраненный порядок изображений из сессии
        logger.info(f'Получаем сохраненный порядок изображений из сессии')
        image_order = session.get('images')
        logger.info(f'Получен сохраненный порядок изображений: {image_order}')

        # Если порядок изображений сохранен, используем его
        if image_order:
            # Проверяем, является ли image_order словарем
            if isinstance(image_order, list):
                # Преобразуем список в словарь
                image_order = {idx + 1: image_name for idx, image_name in enumerate(image_order)}
                session['images'] = image_order  # Обновляем сессию словарем

            # Сортируем изображения по сохраненному порядку
            sorted_images = sorted(image_order.items(), key=lambda x: int(x[0]))
            images = [image_name for _, image_name in sorted_images]
        else:
            # Если порядок не сохранен, собираем изображения из папки
            for f in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, f)
                if os.path.isfile(file_path) and allowed_file(f) and f != 'animation.gif':
                    images.append(f)
    logger.info(f'Получен список изображений: {images}')
    return jsonify(images=images)


@app.route('/get_session_id', methods=['GET'])
def get_session_id():
    """
    Возвращает текущий или новый session_id.
    Возвращает:
    - JSON с session_id
    """
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
    """
    Главная страница приложения.
    Возвращает:
    - HTML шаблон с загруженными изображениями и параметрами для создания GIF
    """
    logger.info('Переход на главную страницу...')
    # Проверяем, есть ли session_id в сессии
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f'Создана новая сессия session_id={session["session_id"]}')

        # Создаем папку для загрузки только при инициализации новой сессии
        upload_folder = os.path.join(uploads_root, session['session_id'])
        if not os.path.exists(upload_folder):
            try:
                os.makedirs(upload_folder, exist_ok=True)
                logger.info(f'Папка успешно создана: {upload_folder}')
            except Exception as e:
                logger.error(f'Ошибка при создании папки: {e}')
                return jsonify(error='Failed to create upload directory'), 500

    session_id = session['session_id']
    logger.info(f'Используем старый session_id={session_id}')

    # Получаем список изображений из папки загрузки
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
                filename = secure_filename(file.filename)  # Безопасное имя файла
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
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
    logger.info('Создаём каталог для загрузки...')
    upload_folder = os.path.join(uploads_root, new_session_id)
    try:
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f'Папка успешно создана: {upload_folder}')
    except Exception as e:
        logger.error(f'Ошибка при создании папки: {e}')
        return jsonify(error='Failed to create upload directory'), 500

    return redirect(url_for('index'))


@app.route('/uploads/<filename>')
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
        return "Session ID not found", 404
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
        return jsonify(error='Session ID не найден'), 400

    logger.info(f'Session ID: {session_id}')

    # Получаем файлы из запроса
    files = request.files.getlist('files')
    if not files:
        return jsonify(error='No files uploaded'), 400

    # Подготавливаем данные для отправки на image_processing
    upload_url = 'http://api/upload'
    headers = {'X-Session-ID': session_id}
    files_data = [('files', (file.filename, file.stream, file.mimetype)) for file in files]

    try:
        # Отправляем запрос на image_processing
        response = requests.post(upload_url, files=files_data, headers=headers)

        # Проверяем статус ответа
        if response.status_code == 200:
            response_data = response.json()
            new_filenames = response_data.get('filenames', [])
            if isinstance(new_filenames, list):
                session.setdefault('images', []).extend(new_filenames)
                return jsonify(success=True, filenames=new_filenames)
            else:
                logger.error(f'Ошибка при загрузке файлов: "filenames" не является списком, получено: {new_filenames}')
                return jsonify(error='Unexpected response format from image_processing'), 500
        else:
            logger.error(f'Ошибка при загрузке файлов: {response.text}')
            return jsonify(error='Failed to upload files'), response.status_code
    except Exception as e:
        logger.error(f'Ошибка при отправке запроса на image_processing: {str(e)}')
        return jsonify(error='Internal server error'), 500


@app.route('/remove_image', methods=['POST'])
def remove_image():
    """
    Удаляет изображение.
    Входные параметры:
    - image_name: Имя файла для удаления
    Возвращает:
    - JSON с успешным статусом или сообщением об ошибке
    """
    session_id = session.get('session_id')
    logger.info(f"@@@ Маршрут Remove Image. Отправляем Session ID из web_ui: {session_id}")
    try:
        image_name = request.form.get('image_name')
        if not image_name:
            return jsonify({'success': False, 'message': 'Имя файла не указано'}), 400

        # Удаляем изображение из сессии
        image_order = session.get('images', {})
        if image_order:
            if isinstance(image_order, dict):
                image_order = {k: v for k, v in image_order.items() if v != image_name}
            elif isinstance(image_order, list):
                image_order = [img for img in image_order if img != image_name]
            session['images'] = image_order

        # Отправляем запрос к микросервису image_processing
        response = requests.post(f'http://api/remove_image',
                                 headers={'X-Session-ID': session_id},
                                 data={'image_name': image_name})

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

    # Преобразуем строку image_order в словарь
    image_order_dict = json.loads(image_order)
    logger.info(f'Received image_order: {image_order_dict}')

    # Отправляем запрос в image_processing для изменения порядка изображений
    reorder_url = 'http://api/reorder_images'
    logger.info(f'Отправляем image_order: {image_order_dict}')

    response = requests.post(reorder_url,
                             headers={'X-Session-ID': session_id},
                             data={'image_order': json.dumps(image_order_dict)})

    if response.status_code == 200:
        # Обновляем порядок изображений в сессии
        session['images'] = image_order_dict  # Убедимся, что сохраняем словарь
        return jsonify(success=True)
    else:
        logger.error(f'Error reordering images: {response.text}')
        return jsonify(success=False, error='Failed to reorder images'), response.status_code


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    """
    Генерирует GIF из загруженных изображений.
    Входные параметры:
    - duration: Длительность кадра в миллисекундах
    - loop: Количество циклов воспроизведения GIF
    - resize: Новые размеры изображений в формате "ШxВ"
    Возвращает:
    - Перенаправление на главную страницу или сообщение об ошибке
    """
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

    # Получаем порядок изображений из сессии
    image_order = session.get('images', {})
    if not image_order:
        return jsonify(error='No image order found in session'), 400

    generate_url = 'http://api/generate_gif'
    headers = {'X-Session-ID': session_id}
    data = {
        'duration': duration,
        'loop': loop,
        'resize': resize,
        'image_order': json.dumps(image_order)  # Добавляем порядок изображений в данные запроса
    }

    response = requests.post(generate_url, headers=headers, data=data)
    if response.status_code == 200:
        response_data = response.json()
        gif_url = response_data.get('gif_url')
        if gif_url:
            return jsonify(success=True, gif_url=gif_url)
        else:
            return jsonify(success=False, error='GIF URL not found in response'), 500
    else:
        logger.error(f'Ошибка при создании GIF: {response.text}')
        return jsonify(error='Failed to generate GIF'), 500


if __name__ == '__main__':
    logger.info('@@@ Запуск сервера...')
    clean_uploads()
    app.run(debug=True, host='0.0.0.0', port=5000)
