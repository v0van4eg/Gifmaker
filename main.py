import os
from flask import Flask, render_template, request, redirect, url_for, session
import imageio.v2 as imageio
import numpy as np
import shutil
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    upload_folder = os.path.join(app.root_path, 'static', 'uploads', session_id)
    app.config['UPLOAD_FOLDER'] = upload_folder
    gif_file = os.path.join(upload_folder, 'animation.gif')

    # Создать папку uploads/<session_id>, если она не существует
    os.makedirs(upload_folder, exist_ok=True)

    if request.method == 'POST':
        session.pop('images', None)
        files = request.files.getlist('files')
        for file in files:
            if allowed_file(file.filename):
                file.save(os.path.join(upload_folder, file.filename))
                session.setdefault('images', []).append(file.filename)

    images = session.get('images', [])
    return render_template('index.html', images=images, gif_file=gif_file)

@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    image_order = request.form.get('image_order').split(',')
    session['images'] = image_order
    return 'OK'

@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    session_id = session['session_id']
    upload_folder = os.path.join(app.root_path, 'static', 'uploads', session_id)
    gif_file = os.path.join(upload_folder, 'animation.gif')
    duration = int(request.form.get('duration', 100))
    loop = int(request.form.get('loop', 0))
    resize = request.form.get('resize')

    images = []
    for image_name in session.get('images', []):
        try:
            image = imageio.imread(os.path.join(upload_folder, image_name))
            images.append(image)
        except OSError as e:
            print(f"Error reading file {image_name}: {e}")
            continue

    if not images:
        return 'No valid images uploaded', 400

    if resize:
        try:
            width, height = map(int, resize.split('x'))
        except ValueError:
            return 'Invalid resize format. Use WxH', 400

        resized_images = []
        for image in images:
            resized_image = np.array(image)
            resized_image = np.resize(resized_image, (height, width, resized_image.shape[2]))
            resized_images.append(resized_image)
        images = resized_images
    else:
        images = [np.array(image) for image in images]

    try:
        with imageio.get_writer(gif_file, mode='I', duration=duration, loop=loop) as writer:
            for image in images:
                writer.append_data(image)
    except Exception as e:
        print(f"Error generating GIF: {e}")
        return 'Error generating GIF', 500

    return redirect(url_for('index'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/new_session', methods=['GET'])
def new_session():
    session_id = session.get('session_id')
    if session_id:
        upload_folder = os.path.join(app.root_path, 'static', 'uploads', session_id)
        gif_file = os.path.join(upload_folder, 'animation.gif')

        # Очистить список загруженных изображений
        session.pop('images', None)

        # Удалить файл с предыдущей GIF-анимацией, если он существует
        if os.path.exists(gif_file):
            os.remove(gif_file)

        # Очистить содержимое папки uploads
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)

        session['session_id'] = str(uuid.uuid4())
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)


