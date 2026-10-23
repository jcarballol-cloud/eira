# SPDX-License-Identifier: EUPL-1.2
from django.shortcuts import render

from apps.tenants.urlutils import module_required, role_required


@module_required("monitor")
@role_required("monitor", "admin")
def today(request):
    return render(request, "monitor/today.html", {"nav": "monitor", "groups": []})
