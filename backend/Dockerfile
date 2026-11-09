FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/venv \
    PATH="/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

FROM base AS prod
RUN uv sync --locked --no-dev
COPY . .
RUN DJANGO_SECRET_KEY=django-insecure-book-plan-build-key POSTGRES_DB=book_plan POSTGRES_USER=book_plan POSTGRES_PASSWORD=book_plan_build \
    python manage.py collectstatic --noinput
RUN useradd --system --create-home app
USER app
ENV WEB_CONCURRENCY=3
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

FROM base AS dev
RUN uv sync --locked
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
