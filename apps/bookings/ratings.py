# SPDX-License-Identifier: EUPL-1.2
"""Valoracións «Que tal foi?»: Ben / Regular / Mal, etiquetas e comentario opcional.

- Integradas no checklist de peche e dispoñibles despois de calquera uso.
- «Mal» pode converterse nunha incidencia (categoría deducida das etiquetas).
- O concello ve agregados e comentarios **sen nome** da persoa.
"""

import datetime as dt
from collections import Counter

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Booking, Rating

# código → (texto, positiva?, categoría de incidencia se é negativa)
TAGS = {
    "clean": (_("Limpa"), True, None),
    "light": (_("Boa iluminación"), True, None),
    "gear": (_("Material en bo estado"), True, None),
    "access": (_("Acceso doado"), True, None),
    "quiet": (_("Tranquila"), True, None),
    "dirty": (_("Sucia"), False, "cleaning"),
    "lights_broken": (_("Luces avariadas"), False, "lighting"),
    "gear_broken": (_("Material roto ou que falta"), False, "damage"),
    "access_problem": (_("Problema coa porta ou o código"), False, "access"),
    "water": (_("Sen auga quente ou duchas mal"), False, "water"),
    "crowded": (_("Había xente na miña franxa"), False, "other"),
}
POSITIVE = [k for k, v in TAGS.items() if v[1]]
NEGATIVE = [k for k, v in TAGS.items() if not v[1]]
SCORE_VALUE = {"good": 100, "ok": 50, "bad": 0}


def tag_choices(positive=None):
    keys = TAGS if positive is None else (POSITIVE if positive else NEGATIVE)
    return [(k, TAGS[k][0]) for k in keys]


def can_rate(booking):
    return (
        booking.status in (Booking.Status.CONFIRMED, Booking.Status.USED)
        and booking.start <= timezone.now()
        and not Rating.objects.filter(booking=booking).exists()
    )


class RatingForm(forms.Form):
    score = forms.ChoiceField(
        label=_("Que tal foi?"),
        choices=Rating.Score.choices,
        widget=forms.RadioSelect,
        required=False,
    )
    tags = forms.MultipleChoiceField(
        label=_("Algo a destacar?"),
        choices=tag_choices(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    comment = forms.CharField(
        label=_("Comentario (opcional)"),
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text=_("O concello le os comentarios sen ver o teu nome."),
    )
    make_incident = forms.BooleanField(
        label=_("Avisar ao concello para que o arranxe"), required=False, initial=True
    )

    def __init__(self, *args, required=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["score"].required = required

    def save(self, booking):
        d = self.cleaned_data
        if not d.get("score"):
            return None
        return save_rating(
            booking,
            d["score"],
            d.get("tags") or [],
            d.get("comment", ""),
            create_incident=d["score"] == Rating.Score.BAD and d.get("make_incident"),
        )


def save_rating(booking, score, tags=(), comment="", create_incident=False):
    from apps.incidents.models import Incident

    tags = [t for t in tags if t in TAGS]
    rating = Rating.objects.create(
        municipality=booking.municipality,
        booking=booking,
        facility=booking.facility,
        score=score,
        tags=tags,
        comment=(comment or "").strip()[:500],
    )
    if score == Rating.Score.BAD and create_incident:
        cats = [TAGS[t][2] for t in tags if TAGS[t][2]]
        category = cats[0] if cats else Incident.Category.OTHER
        labels = ", ".join(str(TAGS[t][0]) for t in tags if not TAGS[t][1])
        incident = Incident.objects.create(
            municipality=booking.municipality,
            facility=booking.facility,
            reporter=booking.user,
            booking=booking,
            category=category,
            source=Incident.Source.CHECKLIST,
            description=" · ".join(
                x for x in [str(_("Valoración: Mal")), labels, rating.comment] if x
            ),
        )
        from apps.incidents.services import notify_staff_new_incident

        notify_staff_new_incident(incident)
        rating.incident = incident
        rating.save(update_fields=["incident"])
    return rating


def stats(tenant, days=90, facility=None, min_n=5):
    """Agregados por instalación: n, reparto, índice 0–100 e etiquetas máis frecuentes."""
    since = timezone.now() - dt.timedelta(days=days)
    qs = Rating.objects.for_tenant(tenant).filter(created_at__gte=since).select_related("facility")
    if facility:
        qs = qs.filter(facility=facility)
    per = {}
    tags_all = Counter()
    for r in qs:
        row = per.setdefault(
            r.facility_id,
            {"facility": r.facility, "n": 0, "good": 0, "ok": 0, "bad": 0, "tags": Counter()},
        )
        row["n"] += 1
        row[r.score] += 1
        row["tags"].update(r.tags)
        tags_all.update(r.tags)
    rows = []
    for row in per.values():
        n = row["n"]
        row["index"] = round((100 * row["good"] + 50 * row["ok"]) / n)
        row["good_pct"] = round(100 * row["good"] / n)
        row["ok_pct"] = round(100 * row["ok"] / n)
        row["bad_pct"] = 100 - row["good_pct"] - row["ok_pct"]
        row["top_tags"] = [(TAGS[t][0], c, TAGS[t][1]) for t, c in row["tags"].most_common(3)]
        row["enough"] = n >= min_n
        rows.append(row)
    rows.sort(key=lambda r: (not r["enough"], -r["index"], -r["n"]))
    total = sum(r["n"] for r in rows)
    return {
        "rows": rows,
        "total": total,
        "index": round(sum(r["index"] * r["n"] for r in rows) / total) if total else None,
        "tags": [(TAGS[t][0], c, TAGS[t][1]) for t, c in tags_all.most_common(8)],
        "comments": qs.exclude(comment="")[:12],
        "min_n": min_n,
        "days": days,
    }
