import os
import shutil
import uuid
import numpy as np
import imageio.v2 as imageio
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Очистка папки uploads при запуске
uploads_root = os.path.join(app.root_path, 'static', 'uploads')
if os.path.exists(uploads_root):
    shutil.rmtree(uploads_root)
os.makedirs(uploads_root, exist_ok=True)


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    upload_folder = os.path.join(uploads_root, session_id)
    os.makedirs(upload_folder, exist_ok=True)

    if request.method == 'POST':
        files = request.files.getlist('files')
        for file in files:
            if allowed_file(file.filename):
                file_path = os.path.join(upload_folder, file.filename)
                file.save(file_path)
                session.setdefault('images', []).append(file.filename)

    images = session.get('images', [])
    gif_file = os.path.join(upload_folder, 'animation.gif')
    return render_template('index.html', images=images, gif_file=gif_file if os.path.exists(gif_file) else None)


@app.route('/remove_image', methods=['POST'])
def remove_image():
    image_name = request.form.get('image_name')
    session_id = session['session_id']
    upload_folder = os.path.join(uploads_root, session_id)
    image_path = os.path.join(upload_folder, image_name)
    if os.path.exists(image_path):
        os.remove(image_path)
        session['images'].remove(image_name)
        return jsonify(success=True)
    return jsonify(success=False), 400


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    image_order = request.form.getlist('image_order[]')
    session['images'] = image_order
    return 'OK'


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    session_id = session['session_id']
    upload_folder = os.path.join(uploads_root, session_id)
    gif_file = os.path.join(upload_folder, 'animation.gif')
    duration = int(request.form.get('duration', 100))
    loop = int(request.form.get('loop', 0))
    resize = request.form.get('resize')
    images = []

    for image_name in session.get('images', []):
        try:
            image = imageio.imread(os.path.join(upload_folder, image_name))
            images.append(image)
        except Exception:
            continue

    if not images:
        return 'No valid images uploaded', 400

    if resize:
        try:
            width, height = map(int, resize.split('x'))
            images = [np.resize(img, (height, width, img.shape[2])) for img in images]
        except ValueError:
            return 'Invalid resize format', 400

    try:
        with imageio.get_writer(gif_file, mode='I', duration=duration, loop=loop) as writer:
            for img in images:
                writer.append_data(img)
    except Exception:
        return 'Error generating GIF', 500

    return redirect(url_for('index'))


@app.route('/new_session')
def new_session():
    session_id = session.get('session_id')
    if session_id:
        upload_folder = os.path.join(uploads_root, session_id)
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)
    session.pop('images', None)
    session['session_id'] = str(uuid.uuid4())
    return redirect(url_for('index'))


def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
