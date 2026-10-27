# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · G: «Busco xente» na reserva e sección «Partidas abertas» na app."""

import datetime as dt

from django import forms
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.facilities.models import FacilityKind
from apps.tenants.urlutils import neighbour_required, treverse

from . import opengames
from .models import GAME_MESSAGES, GameJoin, GameReport, OpenGame
from .views import _own_booking


class PublishForm(forms.Form):
    spots = forms.IntegerField(label=gettext_lazy("Prazas libres"), min_value=1, initial=1)
    level = forms.ChoiceField(
        label=gettext_lazy("Nivel"),
        choices=OpenGame.Level.choices,
        widget=forms.RadioSelect,
        initial=OpenGame.Level.MEDIUM,
    )
    message = forms.CharField(
        label=gettext_lazy("Mensaxe curta (opcional)"),
        max_length=140,
        required=False,
        help_text=gettext_lazy(
            "P. ex. «Buscamos dúas persoas para dobres». Sen teléfonos nin correos."
        ),
    )
    consent = forms.BooleanField(
        label=gettext_lazy(
            "Acepto aparecer nas partidas abertas co meu nome de pila e a inicial do apelido "
            "(nunca o teléfono nin o correo)."
        ),
        required=True,
    )


def _module_on(request):
    if not request.tenant.module_enabled("open_games"):
        raise Http404


@neighbour_required
def publish(request, pk):
    _module_on(request)
    booking = _own_booking(request, pk)
    game = getattr(booking, "open_game", None)
    room = max(1, booking.facility.max_participants - booking.participants)
    form = PublishForm(
        request.POST or None,
        initial={
            "spots": min(room, game.spots if game else 1),
            "level": getattr(game, "level", "medium"),
        },
    )
    form.fields["spots"].max_value = room
    form.fields["spots"].widget.attrs["max"] = room
    if request.method == "POST" and request.POST.get("accion") == "pechar" and game:
        opengames.close(game, request.user)
        messages.success(request, _("A partida xa non aparece en «Partidas abertas»."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    if request.method == "POST" and form.is_valid():
        try:
            game = opengames.publish(
                booking,
                request.user,
                spots=form.cleaned_data["spots"],
                level=form.cleaned_data["level"],
                message=form.cleaned_data["message"],
                consent=form.cleaned_data["consent"],
            )
        except opengames.GameError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Publicada en «Partidas abertas»."))
            return redirect(treverse(request.tenant, "bookings:game", game.pk))
    return render(
        request,
        "bookings/game_publish.html",
        {"booking": booking, "form": form, "game": game, "room": room, "nav": "bookings"},
    )


@neighbour_required
def games(request):
    _module_on(request)
    kind = request.GET.get("deporte", "")
    level = request.GET.get("nivel", "")
    try:
        day = dt.date.fromisoformat(request.GET.get("dia", ""))
    except ValueError:
        day = None
    found = opengames.visible_games(request.tenant, kind=kind, day=day, level=level)
    return render(
        request,
        "bookings/games.html",
        {
            "games": [(g, opengames.public_name(g.booking.user)) for g in found],
            "kinds": FacilityKind.choices,
            "levels": OpenGame.Level.choices,
            "kind": kind,
            "level": level,
            "day": day,
            "nav": "games",
        },
    )


@neighbour_required
def game(request, pk):
    _module_on(request)
    g = get_object_or_404(
        OpenGame.objects.select_related("booking__facility", "booking__user", "municipality"),
        pk=pk,
        active=True,
        hidden_by_reports=False,
    )
    # Do propio concello ou dun próximo da rede
    if g.municipality_id != request.tenant.pk and (
        not request.tenant.region_id or g.municipality.region_id != request.tenant.region_id
    ):
        raise Http404
    organiser = g.booking.user_id == request.user.pk
    mine = GameJoin.objects.filter(game=g, user=request.user).first()
    if request.method == "POST":
        action = request.POST.get("accion")
        try:
            if action == "unirme":
                opengames.request_join(g, request.user, consent=request.POST.get("consent") == "on")
                messages.success(request, _("Solicitude enviada. Avisarémoste cando responda."))
            elif action == "retirarme" and mine:
                opengames.withdraw(mine)
                messages.success(request, _("Retiraches a túa solicitude."))
            elif action in ("aceptar", "rexeitar") and organiser:
                join = get_object_or_404(GameJoin, game=g, pk=request.POST.get("solicitude"))
                opengames.decide(join, request.user, accept=action == "aceptar")
            elif action == "mensaxe":
                opengames.post_message(g, request.user, request.POST.get("codigo", ""))
            elif action == "denunciar" and not organiser:
                opengames.report(g, request.user, request.POST.get("motivo") or "other")
                messages.success(request, _("Grazas. O concello revisará a partida."))
        except opengames.GameError as exc:
            messages.error(request, str(exc))
        return redirect(treverse(request.tenant, "bookings:game", g.pk))
    member = opengames.is_member(g, request.user)
    return render(
        request,
        "bookings/game.html",
        {
            "g": g,
            "organiser_name": opengames.public_name(g.booking.user),
            "organiser": organiser,
            "mine": mine,
            "member": member,
            "requests": [(j, opengames.public_name(j.user)) for j in g.joins.select_related("user")]
            if organiser
            else [],
            "players": [opengames.public_name(j.user) for j in g.accepted().select_related("user")],
            "chat": [(opengames.public_name(m.user), m) for m in g.messages.select_related("user")]
            if member
            else [],
            "presets": GAME_MESSAGES,
            "reasons": GameReport.Reason.choices,
            "nav": "games",
        },
    )
