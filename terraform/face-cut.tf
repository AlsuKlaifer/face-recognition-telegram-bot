resource "yandex_function" "func_face_cut" {
  name               = var.FACE_CUT_FUNCTION_NAME
  runtime            = "python312"
  entrypoint         = "main.handler"
  memory             = 128
  service_account_id = yandex_iam_service_account.service_acc.id
  user_hash          = archive_file.face_cutter_code.output_sha256

  environment = {
    "PHOTOS_BUCKET_NAME" = var.PHOTOS_BUCKET_NAME
    "FACES_BUCKET_NAME"  = var.FACES_BUCKET_NAME
    "ACCESS_KEY"      = yandex_iam_service_account_static_access_key.sa-static-key.access_key
    "SECRET_KEY"      = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
  }

  content {
    zip_filename = archive_file.face_cutter_code.output_path
  }

  mounts {
    name = yandex_storage_bucket.bucket_faces.bucket
    mode = "rw"
    object_storage {
      bucket = yandex_storage_bucket.bucket_faces.bucket
    }
  }

  mounts {
    name = yandex_storage_bucket.bucket_photos.bucket
    mode = "ro"
    object_storage {
      bucket = yandex_storage_bucket.bucket_photos.bucket
    }
  }
}

resource "archive_file" "face_cutter_code" {
  type        = "zip"
  source_dir  = "../code/face-cutter"
  output_path = "../archives/face-cutter.zip"
}

resource "yandex_function_trigger" "task_queue_trigger" {
  name = var.TASK_QUEUE_TRIGGER
  function {
    id                 = yandex_function.func_face_cut.id
    service_account_id = yandex_iam_service_account.service_acc.id
  }
  message_queue {
    batch_cutoff       = "10"
    batch_size         = "1"
    queue_id           = yandex_message_queue.task_queue.arn
    service_account_id = yandex_iam_service_account.service_acc.id
  }
}