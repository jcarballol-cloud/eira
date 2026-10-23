# SPDX-License-Identifier: EUPL-1.2
import io

import qrcode
import qrcode.image.svg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.facilities.models import Facility
from apps.tenants.urlutils import role_required, treverse

from .services import qr_checkin


def qr_svg(data):
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()


@require_http_methods(["GET", "POST"])
def checkin(request, token):
    """Destino do QR fixo pegado na instalación (nivel 0)."""
    facility = get_object_or_404(Facility, municipality=request.tenant, checkin_token=token)
    booking = None
    done = False
    if request.method == "POST":
        booking = qr_checkin(facility, request.user)
        done = True
    return render(request, "access/checkin.html", {"facility": facility, "booking": booking, "done": done})


@role_required("admin", "region_admin", "maintenance")
def facility_qr(request, pk):
    facility = get_object_or_404(Facility, municipality=request.tenant, pk=pk)
    url = request.build_absolute_uri(treverse(request.tenant, "access:checkin", facility.checkin_token))
    if request.GET.get("format") == "svg":
        return HttpResponse(qr_svg(url), content_type="image/svg+xml")
    return render(request, "access/poster.html", {"facility": facility, "url": url, "svg": qr_svg(url)})
