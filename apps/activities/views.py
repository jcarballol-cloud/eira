# SPDX-License-Identifier: EUPL-1.2
from django.shortcuts import render

from apps.tenants.urlutils import module_required

from .models import Activity


@module_required("activities")
def activity_list(request):
    activities = Activity.objects.for_tenant(request.tenant).filter(is_published=True).prefetch_related("groups")
    return render(request, "activities/list.html", {"activities": activities, "nav": "activities"})
