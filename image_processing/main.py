from flask import Flask, request, jsonify
import os
import numpy as np
from PIL import Image, ImageOps

app = Flask(__name__)

UPLOADS_ROOT = '/app/static/uploads'

@app.route('/process', methods=['POST'])
def process_image():
    image_name = request.form.get('image_name')
    session_id = request.form.get('session_id')
    upload_folder = os.path.join(UPLOADS_ROOT, session_id)
    image_path = os.path.join(upload_folder, image_name)
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)
    # Применение ресайза, если указаны размеры
    resize = request.form.get('resize')
    if resize:
        try:
            width, height = map(int, resize.split('x'))
            img = img.resize((width, height), Image.LANCZOS)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid resize format'}), 400
    img.save(image_path)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
