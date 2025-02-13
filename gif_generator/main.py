import os
import numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageOps
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
uploads_root = '/app/static/uploads'


@app.route('/generate_gif', methods=['POST'])
def generate_gif():
    data = request.get_json()
    session_id = data.get('session_id')
    gif_file = data.get('gif_file')
    duration = data.get('duration', 100)
    loop = data.get('loop', 0)
    resize = data.get('resize')
    images = data.get('images', [])
    processed_images = []
    print(f"Received resize parameter: {resize}")
    for image_name in images:
        try:
            response = requests.get(f'http://upload:5002/get_file/{session_id}/{image_name}')
            if response.status_code == 200:
                img = Image.open(response.raw)
                # Исправление ориентации по метаданным EXIF
                img = ImageOps.exif_transpose(img)
                # Применение ресайза, если указаны размеры
                if resize:
                    print(f"Resizing image: {image_name}")
                    try:
                        width, height = map(int, resize.split('x'))
                        print(f"Resizing to {width}x{height}")
                        img = img.resize((width, height), Image.LANCZOS)
                    except ValueError:
                        return jsonify(error='Invalid resize format'), 400
                processed_images.append(np.array(img))
        except Exception as e:
            print(f"Error processing image {image_name}: {e}")
            continue
    if not processed_images:
        return jsonify(error='No valid images uploaded'), 400
    try:
        with imageio.get_writer(gif_file, mode='I', duration=duration / 1000.0, loop=loop) as writer:
            for img in processed_images:
                writer.append_data(img)
    except Exception as e:
        print(f"Error generating GIF: {e}")
        return jsonify(error='Error generating GIF'), 500
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004)
