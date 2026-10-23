#!/bin/sh
# SPDX-License-Identifier: EUPL-1.2
set -e

# Agarda pola base de datos
python - <<'EOF'
import os, sys, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eira.settings")
django.setup()
from django.db import connection
for i in range(60):
    try:
        connection.ensure_connection()
        break
    except Exception as exc:
        print("Agardando pola base de datos…", exc)
        time.sleep(1)
else:
    sys.exit("Base de datos non dispoñible")
EOF

python manage.py migrate --noinput

if [ "${EIRA_SEED_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo --if-empty
fi

exec "$@"
