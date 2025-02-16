import os
import shutil
import uuid
import numpy as np
import imageio.v2 as imageio
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, send_from_directory
from PIL import Image, ImageOps

# Инициализация Flask-приложения
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для работы с сессиями

# Путь к папке uploads
uploads_root = './uploads'
os.makedirs(uploads_root, exist_ok=True)  # Создаём папку uploads, если её нет


# Функция для проверки допустимых расширений файлов
def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))


# Маршрут для обслуживания загруженных файлов
@app.route('/uploads/<session_id>/<filename>')
def uploaded_file(session_id, filename):
    """
    Возвращает файл из папки uploads по указанному session_id и имени файла.
    Используется для отображения загруженных изображений и сгенерированных GIF.
    """
    return send_from_directory(os.path.join(uploads_root, session_id), filename)


# Главная страница приложения
@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Обрабатывает главную страницу. Позволяет загружать изображения, отображает их
    и предоставляет интерфейс для генерации GIF.
    """
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())  # Генерация уникального ID для сессии
    session_id = session['session_id']
    upload_folder = os.path.join(uploads_root, session_id)
    os.makedirs(upload_folder, exist_ok=True)  # Создаём папку для текущей сессии

    if request.method == 'POST':
        files = request.files.getlist('files')  # Получаем список загруженных файлов
        for file in files:
            if allowed_file(file.filename):  # Проверяем, что файл имеет допустимое расширение
                file_path = os.path.join(upload_folder, file.filename)
                file.save(file_path)  # Сохраняем файл на сервере
                print(f"Файл сохранён: {file_path}")
                session.setdefault('images', []).append(file.filename)  # Добавляем файл в сессию

    images = session.get('images', [])  # Получаем список изображений из сессии
    gif_file = os.path.join(upload_folder, 'animation.gif')
    return render_template('index.html', images=images, gif_file=gif_file if os.path.exists(gif_file) else None)


# Маршрут для удаления изображения
@app.route('/remove_image', methods=['POST'])
def remove_image():
    """
    Удаляет изображение из сессии и с сервера.
    """
    image_name = request.form.get('image_name')  # Получаем имя файла для удаления
    session_id = session['session_id']
    upload_folder = os.path.join(uploads_root, session_id)
    image_path = os.path.join(upload_folder, image_name)

    if os.path.exists(image_path):
        os.remove(image_path)  # Удаляем файл с сервера
        session['images'].remove(image_name)  # Удаляем файл из сессии
        return jsonify(success=True)
    return jsonify(success=False), 400


# Маршрут для изменения порядка изображений
@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    """
    Изменяет порядок изображений в сессии на основе переданного списка.
    """
    image_order = request.form.getlist('image_order[]')  # Получаем новый порядок изображений
    session['images'] = image_order  # Обновляем порядок в сессии
    return 'OK'


# Маршрут для генерации GIF
@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    """
    Генерирует GIF из загруженных изображений с указанными параметрами.
    """
    session_id = session['session_id']
    upload_folder = os.path.join(uploads_root, session_id)
    gif_file = os.path.join(upload_folder, 'animation.gif')  # Путь к выходному GIF-файлу
    duration = int(request.form.get('duration', 100))  # Длительность кадра (по умолчанию 100 мс)
    loop = int(request.form.get('loop', 0))  # Количество циклов (0 — бесконечно)
    resize = request.form.get('resize')  # Размеры для ресайза (например, "400x300")
    images = []

    for image_name in session.get('images', []):
        try:
            image_path = os.path.join(upload_folder, image_name)
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img)  # Исправляем ориентацию изображения
            if resize:  # Ресайз изображения, если указаны размеры
                width, height = map(int, resize.split('x'))
                img = img.resize((width, height), Image.LANCZOS)
            images.append(np.array(img))  # Добавляем изображение в список
        except Exception as e:
            print(f"Ошибка обработки изображения {image_name}: {e}")
            continue

    if not images:
        return 'Нет подходящих изображений для создания GIF', 400

    try:
        # Создаём GIF с помощью imageio
        with imageio.get_writer(gif_file, mode='I', duration=duration / 1000.0, loop=loop) as writer:
            for img in images:
                writer.append_data(img)
    except Exception as e:
        print(f"Ошибка генерации GIF: {e}")
        return 'Ошибка генерации GIF', 500

    return redirect(url_for('index'))  # Перенаправляем на главную страницу


# Маршрут для создания новой сессии
@app.route('/new_session')
def new_session():
    """
    Очищает текущую сессию и создаёт новую.
    """
    session_id = session.get('session_id')
    if session_id:
        upload_folder = os.path.join(uploads_root, session_id)
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)  # Удаляем папку текущей сессии
    session.pop('images', None)  # Очищаем список изображений в сессии
    session['session_id'] = str(uuid.uuid4())  # Генерируем новый ID сессии
    return redirect(url_for('index'))  # Перенаправляем на главную страницу


# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

