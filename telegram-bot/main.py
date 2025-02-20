import os
import boto3
import requests
import json

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"

STORAGE_ACCESS_KEY = os.getenv("STORAGE_ACCESS_KEY")
STORAGE_SECRET_KEY = os.getenv("STORAGE_SECRET_KEY")

PHOTOS_BUCKET = os.getenv("PHOTOS_BUCKET_NAME")
FACES_BUCKET = os.getenv("FACES_BUCKET_NAME")

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")

storage_session = boto3.session.Session()
storage_client = storage_session.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=STORAGE_ACCESS_KEY,
    aws_secret_access_key=STORAGE_SECRET_KEY,
)

def fetch_file_path(file_id):
    url = f"{TELEGRAM_API_URL}/getFile"
    try:
        response = requests.get(url, params={"file_id": file_id})
        response.raise_for_status()
        return response.json().get("result", {}).get("file_path")
    except requests.RequestException as e:
        print(f"Failed to get file path: {e}", {"file_id": file_id})
        return None

def download_image(file_path):
    url = f"{TELEGRAM_FILE_URL}/{file_path}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"Failed to download image: {e}", {"file_path": file_path})
        return None

def upload_image(key, image):
    try:
        storage_client.put_object(
            Bucket=PHOTOS_BUCKET,
            Key=f"{key}.jpeg",
            Body=image,
            ContentType="image/jpeg"
        )
    except Exception as e:
        print(f"Failed to upload to bucket: {e}")
        return None

def save_photo(file_id):
    file_path = fetch_file_path(file_id)
    image = download_image(file_path)
    upload_image(file_id, image)

def handle_getface_command():
    unknown_faces = fetch_unknown_faces()

    if not unknown_faces:
        return None, "Новых фото нет"

    face_key = unknown_faces[0]
    photo_url = f"{API_GATEWAY_URL}fetchImage?key={face_key}"

    return photo_url, None

def fetch_unknown_faces():
    unknown_faces = []
    try:
        response = storage_client.list_objects_v2(Bucket=FACES_BUCKET, Prefix="face-")
        if "Contents" in response:
            unknown_faces = [obj['Key'] for obj in response['Contents']]
    except Exception as e:
        print(f"Error fetching objects from S3: {e}")
    return unknown_faces

def rename_face(name, file_id):
    try:
        old_filename = file_id
        template_file_name = old_filename.split("face-")[1]
        new_filename = f"{name.lower()}-{template_file_name}"
        
        storage_client.copy_object(
            CopySource={'Bucket': FACES_BUCKET, 'Key': old_filename},
            Bucket=FACES_BUCKET,
            Key=new_filename
        )
        
        storage_client.delete_object(Bucket=FACES_BUCKET, Key=old_filename)
    except Exception as e:
        print(f"Error renaming face: {e}")
        raise e

def find_faces(name):
    try:
        response = storage_client.list_objects_v2(Bucket=FACES_BUCKET, Prefix=f"{name.lower()}-")
        
        if "Contents" not in response:
            return []

        photo_urls = [
            f"{API_GATEWAY_URL}fetchOriginal?key={obj['Key'].split('__')[1]}"
            for obj in response["Contents"]
        ]

        return photo_urls

    except Exception as e:
        print(f"Error finding photos for {name}: {e}")
        return []

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    return requests.post(url, data=data)

def send_photo(chat_id, photo_url, caption):
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    print(photo_url)
    data = {'chat_id': chat_id, 'photo': photo_url, 'caption': caption}
    return requests.post(url, data=data)

def process_message(chat_id, text):
    answer = handle_text_message(text)
    send_message(chat_id, answer)

def handler(event, context):
    update = json.loads(event['body'])
    print(update)
    message = update["message"]
    message_id = message["message_id"]
    chat_id = message["chat"]["id"]

    if "photo" in message:
        photo = message.get("photo")
        file_id = photo[-1]["file_id"]

        save_photo(file_id)
        send_message(chat_id, "Фото сохранено")

    elif "text" in message:
        text = message["text"]
        if text[0] == "/":
            if text.startswith("/start"):
                send_message(chat_id, "Бот для распознования лиц. Отправь фото")
                return
            elif text.startswith("/getfaces"):
                print("/getfaces")
                photo_url, error = handle_getface_command()
                if error:
                    send_message(chat_id, error)
                    return
                elif error == None:
                    print(photo_url)
                    print(123)
                    send_photo(chat_id, photo_url, f"Ответом на это сообщение пришлите как зовут этого человека\n{photo_url.split("?key=")[1]}")
                    return
            elif text.startswith("/find"):
                parts = text.split(maxsplit=1)
                if len(parts) < 2 :
                    send_message(chat_id, "Укажите имя после команды /find")
                    return

                name = parts[1].strip()
                send_message(chat_id, f"ПОКАЗЫВАЮ {name}")
                return
            else:
                send_message(chat_id, "Не могу найти такую команду")
                return
        else:
            send_message(chat_id, text)
            return

    else:
        send_message(chat_id, "Напиши /start")

    return {"statusCode": 200, "body": "Message processed."}
