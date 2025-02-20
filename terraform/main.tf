terraform {
  required_version = ">= 0.13"

  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
    telegram = {
      source = "yi-jiayu/telegram"
    }
  }
}

provider "yandex" {
  cloud_id                 = "b1g71e95h51okii30p25"
  folder_id                = var.FOLDER_ID
  service_account_key_file = "../keys/key.json"
}

provider "telegram" {
  bot_token = var.TELEGRAM_BOT_TOKEN
}

resource "yandex_function" "cloud_func" {
  name               = "func-hw2-telegram-bot"
  runtime            = "python312"
  entrypoint         = "main.handler"
  memory             = 128
  service_account_id = yandex_iam_service_account.service_acc.id
  user_hash          = archive_file.telegram-bot-code.output_sha256

  environment = {
    "TELEGRAM_BOT_TOKEN" = var.TELEGRAM_BOT_TOKEN
    "PHOTOS_BUCKET_NAME" = var.PHOTOS_BUCKET_NAME
    "FACES_BUCKET_NAME"  = var.FACES_BUCKET_NAME
    "STORAGE_ACCESS_KEY" = yandex_iam_service_account_static_access_key.sa-static-key.access_key
    "STORAGE_SECRET_KEY" = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
    "API_GATEWAY_URL"    = "https://${yandex_api_gateway.gateway.domain}/"
  }

  content {
    zip_filename = archive_file.telegram-bot-code.output_path
  }
}

resource "yandex_api_gateway" "gateway" {
  name        = "image-api-gateway"
  description = "API Gateway для доступа к изображениям в Object Storage"

  spec = <<EOT
  openapi: 3.0.0
  info:
    title: Image API
    version: 1.0.0
  paths:
    /fetchImage:
      get:
        summary: "Получить изображение по ключу"
        parameters:
          - name: key
            in: query
            required: true
            schema:
              type: string
        responses:
          "200":
            description: "Изображение"
            content:
              image/jpeg:
                schema:
                  type: string
                  format: binary
          "400":
            description: "Ошибка: ключ не указан"
          "404":
            description: "Изображение не найдено"
        x-yc-apigateway-integration:
          type: object_storage
          bucket: "${var.FACES_BUCKET_NAME}"
          object: "{key}"
          service_account_id: "${yandex_iam_service_account.service_acc.id}"
          headers:
              Content-Type: "{object.response.content-type}"
              Content-Disposition: "inline"

    /fetchOriginal:
      get:
        summary: "Получить оригинальное изображение по имени"
        parameters:
          - name: key
            in: query
            required: true
            schema:
              type: string
        responses:
          "200":
            description: "Изображение"
            content:
              image/jpeg:
                schema:
                  type: string
                  format: binary
          "400":
            description: "Ошибка: ключ не указан"
          "404":
            description: "Изображение не найдено"
        x-yc-apigateway-integration:
          type: object_storage
          bucket: "${var.PHOTOS_BUCKET_NAME}"
          object: "{key}"
          service_account_id: "${yandex_iam_service_account.service_acc.id}"
          headers:
              Content-Type: "{object.response.content-type}"
              Content-Disposition: "inline"
  EOT
}

resource "archive_file" "telegram-bot-code" {
  type        = "zip"
  source_dir  = "../telegram-bot"
  output_path = "../archives/telegram-bot-code.zip"
}

variable "TELEGRAM_BOT_TOKEN" {
  type = string
}

variable "SERVICE_ACCOUNT_ID" {
  type = string
}

variable "FOLDER_ID" {
  type = string
}

variable "PHOTOS_BUCKET_NAME" {
  type = string
}

variable "FACES_BUCKET_NAME" {
  type = string
}

variable "BUCKET_PHOTOS_TRIGGER" {
  type = string
}

variable "RECOGNIZER_FUNCTION_NAME" {
  type = string
}

variable "TASK_QUEUE_NAME" {
  type = string
}

variable "FACE_CUT_FUNCTION_NAME" {
  type = string
}

variable "TASK_QUEUE_TRIGGER" {
  type = string
}

resource "yandex_iam_service_account" "service_acc" {
  name = "ai-hw2-sa"
}

resource "yandex_iam_service_account_static_access_key" "sa-static-key" {
  service_account_id = yandex_iam_service_account.service_acc.id
}

resource "yandex_resourcemanager_folder_iam_member" "sa_func_invoke_iam" {
  folder_id = var.FOLDER_ID
  role      = "functions.functionInvoker"
  member    = "serviceAccount:${yandex_iam_service_account.service_acc.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "sa_storage_viewer_iam" {
  folder_id = var.FOLDER_ID
  role      = "storage.admin"
  member    = "serviceAccount:${yandex_iam_service_account.service_acc.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "sa_ymq_writer_iam" {
  folder_id = var.FOLDER_ID
  role      = "ymq.admin"
  member    = "serviceAccount:${yandex_iam_service_account.service_acc.id}"
}

resource "yandex_storage_bucket" "bucket_photos" {
  bucket        = var.PHOTOS_BUCKET_NAME
  force_destroy = true
}

resource "yandex_storage_bucket" "bucket_faces" {
  bucket        = var.FACES_BUCKET_NAME
  force_destroy = true
}