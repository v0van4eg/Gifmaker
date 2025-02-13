import os
import uuid
import time
from flask import Flask, request, jsonify, send_from_directory
import shutil

app = Flask(__name__)

# Очистка папки uploads при запуске
uploads_root = './static/uploads'
print('uploads_root')

@app.route('/upload', methods=['POST'])
def upload_file():
    print("Запускем upload_file")
    file = request.files.get('file')
    print(file)
    if file:
        # Получаем session_id из запроса или создаем новый, если его нет
        session_id = request.form.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
        upload_folder = os.path.join(uploads_root, session_id)
        print(upload_folder)
        os.makedirs(upload_folder, exist_ok=True)
        # Генерируем уникальное имя файла с использованием timestamp
        timestamp = int(time.time() * 1000)  # Получаем текущий timestamp в миллисекундах
        if '.' in file.filename:
            file_extension = file.filename.rsplit('.', 1)[1].lower()  # Получаем расширение файла
        else:
            file_extension = 'jpg'  # Дефолтное расширение, если нет точки в имени файла
        unique_filename = f"img_{timestamp}.{file_extension}"
        print(unique_filename)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        return jsonify(session_id=session_id, filename=unique_filename), 200
    return jsonify(error='No file provided'), 400

@app.route('/get_file/<session_id>/<filename>', methods=['GET'])
def get_file(session_id, filename):
    file_path = os.path.join(uploads_root, session_id, filename)
    if os.path.exists(file_path):
        return send_from_directory(os.path.join(uploads_root, session_id), filename)
    return jsonify(error='File not found'), 404

@app.route('/remove_file/<session_id>/<filename>', methods=['DELETE'])
def remove_file(session_id, filename):
    file_path = os.path.join(uploads_root, session_id, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify(success=True), 200
    return jsonify(success=False), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)