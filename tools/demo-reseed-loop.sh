#!/bin/sh
# SPDX-License-Identifier: EUPL-1.2
# Bucle mínimo (sen cron nin dependencias): rexenera os datos ficticios da demo unha vez ao día á
# hora indicada, na zona horaria do contedor (TZ), e executa as tarefas periódicas cada 15 minutos.
RESEED_HOUR="${EIRA_RESEED_HOUR:-4}"
last_day=""
tick=0

# O contedor `app` é quen migra: agardar a que a base de datos estea ao día
until python /app/manage.py migrate --check >/dev/null 2>&1; do
  echo "Agardando a que a aplicación migre a base de datos…"
  sleep 5
done

while true; do
  hour=$(date +%H | sed 's/^0//')
  day=$(date +%F)
  if [ "${hour:-0}" -eq "$RESEED_HOUR" ] && [ "$day" != "$last_day" ]; then
    echo "$(date) rexenerando os datos de demostración"
    if python /app/manage.py seed_demo >/dev/null; then
      last_day="$day"
      echo "$(date) demo rexenerada"
      # Ficheiros subidos polas visitas: os da carga de hoxe quedan, os de onte non
      find /app/media -type f -mmin +1380 -delete
    else
      echo "$(date) a rexeneración fallou; tentarase de novo"
    fi
  fi
  if [ $((tick % 15)) -eq 0 ]; then
    python /app/manage.py booking_maintenance >/dev/null || true
    python /app/manage.py generate_work_orders --days 14 >/dev/null || true
  fi
  tick=$((tick + 1))
  sleep 60
done
