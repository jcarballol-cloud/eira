# SPDX-License-Identifier: EUPL-1.2
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.facilities.models import Facility
from apps.tenants.uploads import clean_image
from apps.tenants.urlutils import treverse

from .models import Incident
from .services import notify_staff_new_incident


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ["facility", "category", "description", "photo"]
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": gettext_lazy("P. ex.: a rede da pista 2 está rota"),
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp", "capture": "environment"}
            ),
            "category": forms.RadioSelect,
        }
        help_texts = {
            "photo": gettext_lazy("Opcional. Eliminamos a localización e outros metadatos da foto.")
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facility"].queryset = Facility.objects.for_tenant(tenant).filter(
            is_published=True
        )
        self.fields["facility"].empty_label = gettext_lazy("Escolle a instalación")

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size") and not isinstance(photo, str):
            return clean_image(photo)
        return photo


@login_required
def new(request):
    initial = {}
    if request.GET.get("instalacion"):
        initial["facility"] = request.GET["instalacion"]
    form = IncidentForm(
        request.POST or None, request.FILES or None, tenant=request.tenant, initial=initial
    )
    if request.method == "POST" and form.is_valid():
        incident = form.save(commit=False)
        incident.municipality = request.tenant
        incident.reporter = request.user
        incident.save()
        notify_staff_new_incident(incident)
        messages.success(
            request,
            _("Grazas! Recibimos o teu aviso (#%(n)s). Avisarémoste cando estea arranxado.")
            % {"n": incident.pk},
        )
        return redirect(treverse(request.tenant, "incidents:detail", incident.pk))
    mine = (
        Incident.objects.for_tenant(request.tenant)
        .filter(reporter=request.user)
        .select_related("facility")[:10]
    )
    return render(request, "incidents/new.html", {"form": form, "mine": mine, "nav": "incident"})


@login_required
def detail(request, pk):
    incident = get_object_or_404(
        Incident, municipality=request.tenant, pk=pk, reporter=request.user
    )
    return render(request, "incidents/detail.html", {"incident": incident, "nav": "incident"})
