# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · E: responder a enquisa anual (veciñanza) e lanzala e ver os resultados (concello)."""

import datetime as dt

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.accounts.models import audit
from apps.facilities.models import Facility
from apps.tenants.urlutils import neighbour_required, role_required, treverse

from . import services
from .models import ASPECTS, NPS_QUESTION, Survey, SurveyResponse

SCORE_CHOICES = [(str(i), str(i)) for i in range(1, 6)] + [("", gettext_lazy("Non sei"))]


class AnswerForm(forms.ModelForm):
    class Meta:
        model = SurveyResponse
        fields = ["nps", *[k for k, _l in ASPECTS], "facility", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "maxlength": 500})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nps"] = forms.TypedChoiceField(
            label=NPS_QUESTION,
            choices=[(str(i), str(i)) for i in range(11)],
            coerce=int,
            widget=forms.RadioSelect,
        )
        for key, label in ASPECTS:
            self.fields[key] = forms.TypedChoiceField(
                label=label,
                choices=SCORE_CHOICES,
                coerce=int,
                empty_value=None,
                required=False,
                widget=forms.RadioSelect,
            )
        self.fields["facility"].queryset = Facility.objects.for_tenant(tenant).filter(
            is_published=True
        )
        self.fields["facility"].required = False
        self.fields["comment"].help_text = gettext_lazy(
            "Non escribas datos persoais. O concello le os comentarios sen saber quen os escribiu."
        )


@neighbour_required
def answer(request):
    survey = services.open_survey(request.tenant)
    done = survey and SurveyResponse.objects.filter(survey=survey, user=request.user).exists()
    form = None
    if survey and not done:
        form = AnswerForm(request.POST or None, tenant=request.tenant)
        if request.method == "POST" and form.is_valid():
            response = form.save(commit=False)
            response.survey = survey
            response.user = request.user
            response.save()
            messages.success(request, _("Grazas! A túa resposta axúdanos a mellorar."))
            return redirect(treverse(request.tenant, "surveys:answer"))
    return render(
        request,
        "surveys/answer.html",
        {
            "survey": survey,
            "done": done,
            "form": form,
            "aspects": [form[k] for k, _l in ASPECTS] if form else [],
            "nav": "home",
        },
    )


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ["year", "title", "opens_on", "closes_on"]
        widgets = {
            "opens_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "closes_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def clean(self):
        data = super().clean()
        if data.get("opens_on") and data.get("closes_on") and data["closes_on"] < data["opens_on"]:
            self.add_error("closes_on", _("A data de peche ten que ser posterior á de apertura."))
        if (
            data.get("year")
            and Survey.objects.filter(municipality=self.tenant, year=data["year"]).exists()
        ):
            self.add_error("year", _("Xa hai unha enquisa dese ano."))
        return data


@role_required("admin", "region_admin")
def manage_list(request):
    t = request.tenant
    today = timezone.localdate()
    form = SurveyForm(
        request.POST or None,
        tenant=t,
        initial={"year": today.year, "opens_on": today, "closes_on": today + dt.timedelta(days=30)},
    )
    if request.method == "POST" and form.is_valid():
        survey = form.save(commit=False)
        survey.municipality = t
        survey.save()
        audit("survey.create", request.user, t, survey)
        messages.success(request, _("Enquisa creada. Avisa á veciñanza cando estea aberta."))
        return redirect(treverse(t, "manage:survey", survey.pk))
    surveys = Survey.objects.filter(municipality=t)
    return render(
        request,
        "manage/surveys.html",
        {
            "surveys": [(s, SurveyResponse.objects.filter(survey=s).count()) for s in surveys],
            "evolution": services.evolution(t),
            "use_nps": services.facility_use_nps(t),
            "form": form,
            "today": today,
            "nav": "manage",
            "sub": "surveys",
        },
    )


@role_required("admin", "region_admin")
def manage_detail(request, pk):
    survey = get_object_or_404(Survey, municipality=request.tenant, pk=pk)
    return render(
        request,
        "manage/survey.html",
        {
            "survey": survey,
            "r": services.results(survey),
            "min_n": services.MIN_N,
            "nav": "manage",
            "sub": "surveys",
        },
    )


@role_required("admin")
@require_POST
def announce(request, pk):
    survey = get_object_or_404(Survey, municipality=request.tenant, pk=pk)
    if not survey.is_open():
        messages.warning(request, _("A enquisa non está aberta: non se pode avisar."))
    else:
        n = services.announce(survey, by=request.user)
        messages.success(request, _("Aviso enviado a %(n)s persoas.") % {"n": n})
    return redirect(treverse(request.tenant, "manage:survey", survey.pk))
