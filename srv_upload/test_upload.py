import unittest
import os
from unittest.mock import MagicMock
from srv_upload.upload import app, allowed_file, redis_client

class TestUpload(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Мокируем Redis
        redis_client.exists = MagicMock(return_value=True)
        redis_client.set = MagicMock(return_value=True)

    def test_upload_valid_files(self):
        # Создаем директорию для загрузки
        upload_dir = '/home/poly/PycharmProjects/Gifmaker/srv_upload/uploads/test_session_id'
        os.makedirs(upload_dir, exist_ok=True)

        with open('test.jpg', 'rb') as f:
            data = {'files': (f, 'test.jpg')}
            headers = {'X-Session-ID': 'test_session_id'}
            response = self.app.post('/upload', data=data, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        self.assertIn('filenames', response.json)

    def test_upload_no_session_id(self):
        with open('test.jpg', 'rb') as f:
            data = {'files': (f, 'test.jpg')}
            response = self.app.post('/upload', data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json)  # Проверяем наличие ключа 'error'
        self.assertFalse(response.json.get('success', False))  # Проверяем success, если он есть

    def test_upload_no_files(self):
        headers = {'X-Session-ID': 'test_session_id'}
        response = self.app.post('/upload', headers=headers)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json)  # Проверяем наличие ключа 'error'
        self.assertFalse(response.json.get('success', False))  # Проверяем success, если он есть

    def test_allowed_file_valid(self):
        valid_extensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']
        for ext in valid_extensions:
            filename = f'test.{ext}'
            self.assertTrue(allowed_file(filename))

    def test_allowed_file_invalid(self):
        invalid_extensions = ['txt', 'pdf']
        for ext in invalid_extensions:
            filename = f'test.{ext}'
            self.assertFalse(allowed_file(filename))

if __name__ == '__main__':
    unittest.main()