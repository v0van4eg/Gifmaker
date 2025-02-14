# image_processing/main.py

from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
uploads_root = os.path.join(app.root_path, 'uploads')


@app.route('/remove_image', methods=['POST'])
def remove_image():
    image_name = request.form.get('image_name')
    if not image_name:
        return jsonify(error='Image name not provided'), 400

    image_path = os.path.join(uploads_root, image_name)
    if os.path.exists(image_path):
        os.remove(image_path)
        return jsonify(success=True)
    else:
        return jsonify(error='Image not found'), 404


@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    image_order = request.form.get('image_order')
    if not image_order:
        return jsonify(error='Image order not provided'), 400

    image_order = image_order.split(',')
    for idx, image_name in enumerate(image_order):
        old_path = os.path.join(uploads_root, image_name)
        new_path = os.path.join(uploads_root, f'{idx:04d}_{image_name}')
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

    # Rename back to original names
    for idx, image_name in enumerate(image_order):
        old_path = os.path.join(uploads_root, f'{idx:04d}_{image_name}')
        new_path = os.path.join(uploads_root, image_name)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

    return jsonify(success=True)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)