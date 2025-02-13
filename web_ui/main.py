import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import shutil
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Очистка папки uploads при запуске
uploads_root = os.path.join(os.getcwd(), 'static', 'uploads')
print(uploads_root)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    if request.method == 'POST':
        files = request.files.getlist('files')
        for file in files:
            response = requests.post('http://localhost:5002/upload', files={'file': file})
            if response.status_code == 200:
                session.setdefault('images', []).append(response.json().get('filename'))
    images = session.get('images', [])
    gif_file = os.path.join(uploads_root, session_id, 'animation.gif')
    return render_template('index.html', images=images, gif_file=gif_file if os.path.exists(gif_file) else None)

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('files')
    for file in files:
        response = requests.post('http://localhost:5002/upload', files={'file': file})
        if response.status_code == 200:
            session_id = response.json().get('session_id')
            filename = response.json().get('filename')
            session['session_id'] = session_id
            session.setdefault('images', []).append(filename)
    return redirect(url_for('index'))

@app.route('/remove_image', methods=['POST'])
def remove_image():
    image_name = request.form.get('image_name')
    session_id = session['session_id']
    response = requests.delete(f'http://localhost:5002/remove_file/{session_id}/{image_name}')
    if response.status_code == 200:
        session['images'].remove(image_name)
        return jsonify(success=True)
    return jsonify(success=False), 400

@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    image_order = request.form.getlist('image_order[]')
    session['images'] = image_order
    response = requests.post('http://image_processing:5003/reorder_images', json={'session_id': session['session_id'], 'image_order': image_order})
    if response.status_code == 200:
        return 'OK'
    return 'Error', 400

@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    session_id = session['session_id']
    gif_file = os.path.join(uploads_root, session_id, 'animation.gif')
    duration = request.form.get('duration', 100)
    loop = request.form.get('loop', 0)
    resize = request.form.get('resize')
    images = session.get('images', [])

    response = requests.post(
        'http://localhost:5004/generate_gif',
        json={
            'session_id': session_id,
            'gif_file': gif_file,
            'duration': int(duration),
            'loop': int(loop),
            'resize': resize,
            'images': images
        }
    )

    if response.status_code == 200 and response.json().get('success'):
        return redirect(url_for('index'))
    else:
        return jsonify(error=response.json().get('error')), response.status_code

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