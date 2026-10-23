#!/bin/sh
# SPDX-License-Identifier: EUPL-1.2
# Bucle mínimo (sen cron nin dependencias): rexenera os datos ficticios da demo unha vez ao día
# á hora indicada (UTC) e executa as tarefas periódicas cada 15 minutos.
RESEED_HOUR="${EIRA_RESEED_HOUR_UTC:-4}"
last_day=""

# O contedor `app` é quen migra: agardar a que a base de datos estea ao día
until python /app/manage.py migrate --check >/dev/null 2>&1; do
  echo "Agardando a que a aplicación migre a base de datos…"
  sleep 5
done

while true; do
  hour=$(date -u +%H | sed 's/^0//')
  day=$(date -u +%F)
  if [ "${hour:-0}" -eq "$RESEED_HOUR" ] && [ "$day" != "$last_day" ]; then
    echo "$(date -u) rexenerando os datos de demostración"
    python /app/manage.py seed_demo && last_day="$day"
  fi
  python /app/manage.py booking_maintenance || true
  python /app/manage.py generate_work_orders --days 14 || true
  sleep 900
done
