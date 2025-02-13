from flask import Flask, request, jsonify
import os
import numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageOps

app = Flask(__name__)

UPLOADS_ROOT = '/app/static/uploads'

@app.route('/generate', methods=['POST'])
def generate_gif():
    session_id = request.form.get('session_id')
    upload_folder = os.path.join(UPLOADS_ROOT, session_id)
    gif_file = os.path.join(upload_folder, 'animation.gif')
    duration = int(request.form.get('duration', 100))
    loop = int(request.form.get('loop', 0))
    resize = request.form.get('resize')
    images = []
    for image_name in request.form.getlist('images[]'):
        try:
            image_path = os.path.join(upload_folder, image_name)
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img)
            if resize:
                try:
                    width, height = map(int, resize.split('x'))
                    img = img.resize((width, height), Image.LANCZOS)
                except ValueError:
                    return jsonify({'status': 'error', 'message': 'Invalid resize format'}), 400
            images.append(np.array(img))
        except Exception as e:
            print(f"Error processing image {image_name}: {e}")
            continue
    if not images:
        return jsonify({'status': 'error', 'message': 'No valid images uploaded'}), 400
    try:
        with imageio.get_writer(gif_file, mode='I', duration=duration / 1000, loop=loop) as writer:
            for img in images:
                writer.append_data(img)
    except Exception as e:
        print(f"Error generating GIF: {e}")
        return jsonify({'status': 'error', 'message': 'Error generating GIF'}), 500
    return jsonify({'status': 'success', 'gif_file': f'/static/uploads/{session_id}/animation.gif'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004)
