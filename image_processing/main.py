import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/remove_image', methods=['POST'])
def remove_image():
    data = request.get_json()
    session_id = data.get('session_id')
    image_name = data.get('image_name')
    response = requests.delete(f'http://upload:5002/remove_file/{session_id}/{image_name}')
    if response.status_code == 200:
        return jsonify(success=True), 200
    return jsonify(success=False), 400

@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    data = request.get_json()
    session_id = data.get('session_id')
    image_order = data.get('image_order', [])
    upload_folder = os.path.join(os.getenv('UPLOADS_ROOT', os.path.join(os.getcwd(), 'uploads')), session_id)
    current_images = [f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))]
    ordered_images = []
    for image_name in image_order:
        if image_name in current_images:
            ordered_images.append(image_name)
    # Переупорядочивание файлов
    for i, image_name in enumerate(ordered_images):
        src = os.path.join(upload_folder, image_name)
        dst = os.path.join(upload_folder, f"{i+1}_{image_name}")
        os.rename(src, dst)
    return 'OK', 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
