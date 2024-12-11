# Авторизационный сервис с OAuth2 для Google

Этот проект представляет собой сервис авторизации на основе FastAPI, который использует OAuth2 для входа через Google. В проекте реализована регистрация и авторизация пользователей, а также управление ролями.

## Основные возможности

- **Google OAuth2**: Пользователи могут авторизоваться через Google, используя OAuth2.
- **JWT Токены**: После успешной авторизации генерируются JWT токены для доступа и обновления.
- **Роли пользователей**: Реализована система ролей, включая роль по умолчанию ("default").
- **Хранение данных**: Данные пользователей и ролей сохраняются в базе данных PostgreSQL.

## Запуск проекта

1. Установите зависимости:
    ```
    pip install -r requirements.txt
    ```

2. Переименуйте файл `.env.dist` в корне проекта и добавьте необходимые переменные:
    ```
   # Postgres
    POSTGRES_SERVER=localhost
    POSTGRES_PORT=5432
    POSTGRES_USER=your_user
    POSTGRES_PASSWORD=your_password
    POSTGRES_DB=your_db
   
   # JWT settings
    SECRET_KEY=your_secret_key
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # Google OAuth2
    GOOGLE_CLIENT_ID=your_google_client_id
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    ```

3. Запустите приложение:
    ```
    uvicorn app.main:app --reload
    ```

4. Сервис будет доступен по адресу `http://127.0.0.1:8000`.

## Структура проекта

- `app/`: Основная папка с кодом приложения.
  - `api/`: Роуты и логика работы с пользователями и ролями.
  - `core/`: Конфигурация приложения, подключение к базе данных и безопасность.
  - `templates/`: HTML-шаблоны для страниц регистрации, логина и панели управления.

## Основные ссылки
- **Страница регистрации**: `http://127.0.0.1:8000/register`
- **Страница входа**: `http://127.0.0.1:8000/login`
- **Панель управления**: `http://127.0.0.1:8000/dashboard`
- **OAuth2 Google авторизация**: `http://127.0.0.1:8000/auth/google`
- **Callback от Google**: `http://127.0.0.1:8000/auth/google/callback`
- 
## Docker

Для создания Docker-образа для данного приложения используйте следующий Dockerfile:

    ```
    # Используем официальный образ Python
    FROM python:3.11-slim

    # Устанавливаем зависимости
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Копируем весь проект
    COPY . /app/

    # Открываем порт
    EXPOSE 8000

    # Запуск приложения
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

1. Соберите образ:
    ```
    docker build -t auth-service .
    ```

2. Запустите контейнер:
    ```
    docker run -d -p 8000:8000 auth-service
    ```

Сервис будет доступен по адресу `http://127.0.0.1:8000`.

## Использование с Kubernetes

1. Создайте `k8s` манифесты для деплоя, синглтонов и сервисов.
2. Используйте Docker-образ для деплоя вашего сервиса в Kubernetes.
