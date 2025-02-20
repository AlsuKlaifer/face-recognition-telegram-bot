resource "yandex_function" "func_recognizer" {
  name               = var.RECOGNIZER_FUNCTION_NAME
  runtime            = "python312"
  entrypoint         = "main.handler"
  memory             = 128
  service_account_id = yandex_iam_service_account.service_acc.id
  user_hash          = archive_file.face_recognition_code.output_sha256

  environment = {
    "PHOTOS_BUCKET_NAME" = var.PHOTOS_BUCKET_NAME
    "ACCESS_KEY"      = yandex_iam_service_account_static_access_key.sa-static-key.access_key
    "SECRET_KEY"      = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
    "QUEUE_ID"           = yandex_message_queue.task_queue.id
  }

  content {
    zip_filename = archive_file.face_recognition_code.output_path
  }

  mounts {
    name = yandex_storage_bucket.bucket_photos.bucket
    mode = "ro"
    object_storage {
      bucket = yandex_storage_bucket.bucket_photos.bucket
    }
  }
}

resource "archive_file" "face_recognition_code" {
  type        = "zip"
  source_dir  = "../code/face-recognition"
  output_path = "../archives/face-recognition.zip"
}

resource "yandex_function_trigger" "bucket_photos_trigger" {
  name = var.BUCKET_PHOTOS_TRIGGER
  function {
    id                 = yandex_function.func_recognizer.id
    service_account_id = yandex_iam_service_account.service_acc.id
  }
  object_storage {
    bucket_id    = yandex_storage_bucket.bucket_photos.id
    suffix       = ".jpeg"
    create       = true
    batch_cutoff = "1"
  }
}

resource "yandex_message_queue" "task_queue" {
  name                       = var.TASK_QUEUE_NAME
  visibility_timeout_seconds = 600
  receive_wait_time_seconds  = 20
  access_key                 = yandex_iam_service_account_static_access_key.sa-static-key.access_key
  secret_key                 = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
}