# SPDX-License-Identifier: EUPL-1.2
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eira.settings")
application = get_wsgi_application()
