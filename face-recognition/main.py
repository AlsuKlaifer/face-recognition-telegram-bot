import os
import boto3
from json import dumps
import cv2

# Получение переменных окружения
PHOTO_BUCKET = os.getenv("PHOTOS_BUCKET_NAME")
QUEUE_URL = os.getenv("QUEUE_ID")
ACCESS_KEY = os.getenv("SA_ACCESS_KEY")
SECRET_KEY = os.getenv("SA_SECRET_KEY")

# Инициализация клиента для работы с очередью
print("Инициализация клиента SQS...")
sqs_client = boto3.client(
    service_name="sqs",
    endpoint_url="https://message-queue.api.cloud.yandex.net",
    region_name="ru-central1",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)
print("Клиент SQS инициализирован.")

# Функция для поиска лиц на изображении
def find_faces(img_path):
    image = cv2.imread(img_path)
    if image is None:
        raise ValueError(f"Не удалось загрузить изображение: {img_path}")

    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        raise ValueError("Не удалось загрузить классификатор.")

    faces = face_cascade.detectMultiScale(
        gray_image,
        scaleFactor=1.05,
        minNeighbors=6,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    return [list(map(int, face)) for face in faces]

# Основная функция обработки события
def handler(event, context):
    print("Запуск функции process_event...")
    try:
        # Получение идентификатора объекта из события
        print("Получение object_id из события...")
        obj_id = event['messages'][0]['details']['object_id']
        print(f"object_id: {obj_id}")

        # Формирование пути к изображению
        img_path = f"/function/storage/{PHOTO_BUCKET}/{obj_id}"
        print(f"Путь к изображению: {img_path}")

        # Поиск лиц на изображении
        print("Поиск лиц на изображении...")
        faces = find_faces(img_path)

        if not faces:
            print("Лица не обнаружены.")
            return

        # Отправка данных о найденных лицах в очередь
        print("Отправка данных в очередь...")
        for face in faces:
            sqs_client.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=dumps({"object_id": obj_id, "rectangle": face})
            )
        print(f"Отправлено {len(faces)} сообщений в очередь.")

    except Exception as e:
        print(f"Произошла ошибка в process_event: {e}")
    finally:
        print("Завершение функции process_event.")