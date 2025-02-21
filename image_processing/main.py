import time
from flask import Flask, request, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
import logging
import redis

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

redis_host = os.getenv('REDIS_HOST', 'redis')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

uploads_root = os.path.join(app.root_path, 'uploads')


def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))


@app.route('/upload', methods=['POST'])
def upload():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    upload_folder = os.path.join(uploads_root, session_id)
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    files = request.files.getlist('files')
    if not files:
        return jsonify(error='No selected files'), 400

    new_filenames = []
    for file in files:
        if file and allowed_file(file.filename):
            unix_time = int(time.time())
            original_filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())[:8]
            filename = f"IMG_{unix_time}_{unique_id}_{original_filename}"
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            new_filenames.append(filename)

    # Сохраняем имена файлов в Redis
    for idx, filename in enumerate(new_filenames, start=1):
        redis_client.hset(f'session:{session_id}:images', str(idx), filename)

    return jsonify(success=True, filenames=new_filenames)


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    image_order_json = request.form.get('image_order')
    if not image_order_json:
        return jsonify(error='Image order not provided'), 400

    image_order = json.loads(image_order_json)
    redis_client.hmset(f'session:{session_id}:images', image_order)

    return jsonify(success=True)


@app.route('/remove_image', methods=['POST'])
def remove_image():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify(error='Session ID not found'), 400

    image_name = request.form.get('image_name')
    if not image_name:
        return jsonify(error='Image name not provided'), 400

    upload_folder = os.path.join(uploads_root, session_id)
    image_path = os.path.join(upload_folder, image_name)
    if os.path.exists(image_path):
        os.remove(image_path)
        redis_client.hdel(f'session:{session_id}:images', image_name)
        return jsonify(success=True)
    else:
        return jsonify(error='Image not found'), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)