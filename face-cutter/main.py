import os
import boto3
import json
import uuid
from io import BytesIO
from PIL import Image

# Получение переменных окружения
PHOTO_BUCKET = os.getenv("PHOTOS_BUCKET_NAME")
FACES_BUCKET = os.getenv("FACES_BUCKET_NAME")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

# Инициализация клиента для S3
s3 = boto3.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)

def extract_face(image_path, face_coords, output_filename):
    """
    Вырезает лицо из изображения и сохраняет его.
    """
    try:
        with Image.open(image_path) as img:
            x, y, w, h = map(int, face_coords)
            print(f"Вырезаем лицо с координатами: x={x}, y={y}, ширина={w}, высота={h}")

            # Вырезаем область лица
            face = img.crop((x, y, x + w, y + h))

            # Сохраняем вырезанное лицо в буфер
            buffer = BytesIO()
            face.save(buffer, format="JPEG")
            buffer.seek(0)

            # Загружаем вырезанное лицо в S3
            s3.put_object(
                Bucket=FACES_BUCKET,
                Key=output_filename,
                Body=buffer.getvalue(),
                ContentType="image/jpeg"
            )

            print(f"Вырезанное лицо сохранено в S3: {output_filename}")
            return True

    except Exception as e:
        print(f"Ошибка при вырезании лица: {e}")
        raise e

def handler(event, context):
    try:
        print("Обработка события...")
        print(event)

        # Извлекаем данные из сообщения
        message = json.loads(event['messages'][0]['details']['message']['body'])
        object_id = message['object_id']
        face_coords = message['rectangle']

        # Формируем пути и имени файлов
        source_path = f"/function/storage/{PHOTO_BUCKET}/{object_id}"
        output_filename = f"face-{str(uuid.uuid4())}___{object_id}"

        # Вырезаем лицо и сохраняем его
        success = extract_face(source_path, face_coords, output_filename)

        if success:
            return {
                'statusCode': 200,
                'body': '{"status": "success"}'
            }

        raise RuntimeError("Не удалось обработать изображение")

    except Exception as e:
        print(f"Ошибка выполнения: {e}")
        return {
            'statusCode': 500,
            'body': '{"status": "error"}'
        }