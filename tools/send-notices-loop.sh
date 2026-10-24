#!/bin/sh
# SPDX-License-Identifier: EUPL-1.2
# Envía os avisos programados do concello cada 5 minutos (sen cron nin dependencias).
# Mesma orde ca en produción con cron/systemd: `python manage.py send_notices`.
INTERVAL="${EIRA_NOTICES_INTERVAL:-300}"

# O contedor `app` é quen migra: agardar a que a base de datos estea ao día
until python /app/manage.py migrate --check >/dev/null 2>&1; do
  echo "Agardando a que a aplicación migre a base de datos…"
  sleep 5
done

while true; do
  python /app/manage.py send_notices || echo "$(date -u) send_notices fallou; tentarase de novo"
  sleep "$INTERVAL"
done
