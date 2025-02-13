from flask import Flask, request, jsonify
import os
import shutil
import uuid

app = Flask(__name__)

UPLOADS_ROOT = '/app/static/uploads'
sessions = {}

@app.route('/new_session')
def new_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {'images': []}
    upload_folder = os.path.join(UPLOADS_ROOT, session_id)
    os.makedirs(upload_folder, exist_ok=True)
    return jsonify({'session_id': session_id})

@app.route('/remove_image', methods=['POST'])
def remove_image():
    image_name = request.form.get('image_name')
    session_id = request.form.get('session_id')
    upload_folder = os.path.join(UPLOADS_ROOT, session_id)
    image_path = os.path.join(upload_folder, image_name)
    if os.path.exists(image_path):
        os.remove(image_path)
        sessions[session_id]['images'].remove(image_name)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Image not found'}), 400

@app.route('/reorder_images', methods=['POST'])
def reorder_images():
    image_order = request.form.getlist('image_order[]')
    session_id = request.form.get('session_id')
    sessions[session_id]['images'] = image_order
    return 'OK'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
    