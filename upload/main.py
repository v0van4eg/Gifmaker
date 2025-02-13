from flask import Flask, request, jsonify
import os

app = Flask(__name__)

UPLOADS_ROOT = '/app/static/uploads'


@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('files')
    session_id = request.form.get('session_id')
    upload_folder = os.path.join(UPLOADS_ROOT, session_id)
    os.makedirs(upload_folder, exist_ok=True)
    for file in files:
        if allowed_file(file.filename):
            file_path = os.path.join(upload_folder, file.filename)
            file.save(file_path)
    return jsonify({'status': 'success'})


def allowed_file(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
