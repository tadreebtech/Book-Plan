# Book&Plan

[![CI](https://github.com/tadreebtech/Book-Plan/actions/workflows/ci.yml/badge.svg)](https://github.com/tadreebtech/Book-Plan/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2_LTS-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)

## Стек

- Python 3.13, Django 5.2 LTS, Django REST Framework
- PostgreSQL 18
- Docker, Docker Compose
- GitHub Actions

## Требования

- Docker и Docker Compose для запуска
- Python 3.13 и [uv](https://docs.astral.sh/uv/) для локальной разработки

## Быстрый старт

Конфигурация и запуск backend с PostgreSQL в Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

При старте контейнера `backend` выполняется `manage.py migrate`, затем запускается сервер разработки.

- API: <http://localhost:8000/api/v1/>
- Django admin: <http://localhost:8000/admin/>

Создание первого пользователя:

```bash
docker compose exec backend python manage.py createsuperuser
```

## Локальная разработка

PostgreSQL работает в контейнере, backend запускается на хосте:

```bash
cp .env.example .env
docker compose up -d db
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 8000
```

В `.env` должно быть `POSTGRES_HOST=localhost`: значение `db` подходит только для контейнеров Compose.

## Конфигурация

Параметры передаются через переменные окружения. Значения процесса приоритетнее файла `.env`.

```bash
DJANGO_SECRET_KEY=       # секретный ключ Django
DEBUG=                   # режим отладки
DJANGO_ALLOWED_HOSTS=    # допустимые хосты через запятую
POSTGRES_DB=             # имя базы данных
POSTGRES_USER=           # пользователь БД
POSTGRES_PASSWORD=       # пароль пользователя БД
POSTGRES_HOST=           # localhost на хосте, db в Docker Compose
POSTGRES_PORT=           # порт БД, по умолчанию 5432
```

## Команды

Выполняются из `backend/`.

```bash
uv run python manage.py migrate                # применить миграции
uv run python manage.py makemigrations <app>   # создать миграцию
uv run python manage.py check                  # проверить конфигурацию проекта
```

## Тестирование и lint

Тесты выполняются на PostgreSQL: SQLite не поддерживает exclusion constraint, на котором построен запрет пересечения броней.

```bash
docker compose up -d db
cd backend
uv run pytest                                  # тесты
uv run flake8 .                                # lint
uv run black .                                 # форматирование
```

## Структура репозитория

```text
Book-Plan/
├── .github/
│   ├── workflows/ci.yml            # lint, тесты, сборка образа
│   └── dependabot.yml              # обновление зависимостей
├── backend/
│   ├── config/
│   │   ├── django/base.py          # настройки Django
│   │   ├── env.py                  # чтение переменных окружения
│   │   ├── urls.py                 # /admin/ и /api/v1/
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── common/
│   │   │   ├── models.py           # BaseModel (created_at, updated_at)
│   │   │   ├── exceptions.py       # единый формат ошибок API
│   │   │   └── tests/
│   │   ├── accounts/
│   │   │   ├── models.py           # User, Role, AuditLog
│   │   │   ├── permissions.py      # IsAdminRole
│   │   │   ├── selectors.py        # чтение пользователей
│   │   │   ├── services.py         # блокировка и разблокировка
│   │   │   ├── apis.py             # админ-API пользователей
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── migrations/
│   │   │   └── tests/apis/
│   │   └── bookings/
│   │       ├── models.py           # Resource, Booking, constraints
│   │       ├── selectors.py        # список объявлений
│   │       ├── services.py         # создание и отмена брони
│   │       ├── serializers.py
│   │       ├── views.py            # API броней и объявлений
│   │       ├── exceptions.py
│   │       ├── urls.py
│   │       ├── admin.py
│   │       ├── migrations/
│   │       └── tests/              # models, selectors, services, API
│   ├── manage.py
│   ├── Dockerfile
│   ├── pyproject.toml              # зависимости, настройки Black и pytest
│   ├── uv.lock
│   └── .flake8
├── docs/
│   └── api-users.md                # API пользователей для администратора
├── docker-compose.yml              # PostgreSQL и backend
├── .env.example
└── README.md
```

## REST API

Базовый путь: `/api/v1/`.

### Аутентификация

Поддерживаются HTTP Basic и сессия Django. Неаутентифицированный запрос получает `403 UNAUTHORIZED`.

### Бронирования

Доступны любому аутентифицированному пользователю. Пользователь видит только свои брони.

- `GET /bookings/`: список броней
- `GET /bookings/{id}/`: бронь по идентификатору
- `POST /bookings/`: создание брони
- `POST /bookings/{id}/cancel/`: отмена брони

### Администрирование

Доступно пользователю с ролью `ADMIN`. Остальным возвращается `403 ACCESS_DENIED`.

- `GET /admin/users/`: список пользователей
- `GET /admin/users/{id}/`: карточка пользователя
- `POST /admin/users/{id}/block/`: блокировка пользователя
- `POST /admin/users/{id}/unblock/`: разблокировка пользователя
- `GET /admin/listings/`: список объявлений

Подробности по пользователям: [docs/api-users.md](docs/api-users.md).

### Пагинация

Списки `/admin/users/` и `/admin/listings/` принимают `page` (с 1) и `page_size` (от 1 до 100, по умолчанию 20).

### Фильтры

- `/admin/users/`: `search`, `role`, `is_active`, `ordering`
- `/admin/listings/`: `search`, `moderation_status`, `category`, `provider`

### Создание брони

`POST /api/v1/bookings/`

```json
{
  "resource": 1,
  "start_at": "2026-12-01T10:00:00+03:00",
  "end_at": "2026-12-01T12:00:00+03:00",
  "guests": 5
}
```

### Формат ошибок

```json
{
  "code": "BOOKING_CONFLICT",
  "message": "The selected resource is not available.",
  "details": {}
}
```

- `400 VALIDATION_ERROR`: некорректные параметры запроса или тело
- `403 UNAUTHORIZED`: нет действующей аутентификации
- `403 ACCESS_DENIED`: недостаточно прав
- `404 NOT_FOUND`: объект не найден
- `409 BOOKING_CONFLICT`: ресурс занят на выбранный период

## Документация

- [API пользователей для администратора](docs/api-users.md)
