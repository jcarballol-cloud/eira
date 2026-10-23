# SPDX-License-Identifier: EUPL-1.2
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# gettext só para `makemessages` (extracción de cadeas); a compilación faise con polib.
RUN apt-get update && apt-get install -y --no-install-recommends gettext && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python tools/compile_messages.py \
 && EIRA_SECRET_KEY=build-only python manage.py collectstatic --noinput -v0 \
 && useradd --create-home --uid 1000 eira && mkdir -p /app/media && chown -R eira /app/media
USER eira

EXPOSE 8000
ENTRYPOINT ["sh", "/app/tools/docker-entrypoint.sh"]
CMD ["gunicorn", "eira.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
