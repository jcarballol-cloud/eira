# SPDX-License-Identifier: EUPL-1.2
"""API REST aberta (v1). Lectura pública de concellos, instalacións e dispoñibilidade;
reservas e incidencias para persoas autenticadas. Esquema OpenAPI 3.1 en /api/schema/."""

import datetime as dt

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.bookings import services as booking_services
from apps.bookings.models import Booking
from apps.facilities.models import Facility, OpeningHours, Tariff
from apps.incidents.models import Incident
from apps.incidents.services import notify_staff_new_incident
from apps.tenants.models import Municipality


class MunicipalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipality
        fields = [
            "slug",
            "name",
            "ine_code",
            "accent_color",
            "languages",
            "contact_email",
            "contact_phone",
            "cancellation_hours",
            "max_advance_days",
        ]


class OpeningHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpeningHours
        fields = ["weekday", "opens", "closes", "season_start", "season_end"]


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ["audience", "price_cents"]


class FacilitySerializer(serializers.ModelSerializer):
    parish = serializers.CharField(source="parish.name", default=None, read_only=True)
    opening_hours = OpeningHoursSerializer(many=True, read_only=True)
    tariffs = TariffSerializer(many=True, read_only=True)
    rules_version = serializers.SerializerMethodField()

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "kind",
            "parish",
            "description",
            "address",
            "latitude",
            "longitude",
            "indoor",
            "lighting",
            "step_free",
            "adapted_toilet",
            "adapted_changing",
            "accessible_parking",
            "capacity",
            "slot_minutes",
            "access_level",
            "opening_hours",
            "tariffs",
            "rules_version",
        ]

    def get_rules_version(self, obj) -> int | None:
        r = obj.current_rules()
        return r.version if r else None


class SlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    status = serializers.CharField()
    booked = serializers.IntegerField()
    capacity = serializers.IntegerField()


class BookingSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "reference",
            "facility",
            "facility_name",
            "start",
            "end",
            "status",
            "price_cents",
            "paid_cents",
            "rules_accepted_at",
        ]
        read_only_fields = [
            "reference",
            "end",
            "status",
            "price_cents",
            "paid_cents",
            "rules_accepted_at",
        ]


class BookingCreateSerializer(serializers.Serializer):
    facility = serializers.IntegerField()
    start = serializers.DateTimeField()
    accept_rules_version = serializers.IntegerField(
        help_text="Versión das normas que a persoa acepta expresamente"
    )


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = ["id", "facility", "category", "description", "status", "created_at"]
        read_only_fields = ["status", "created_at"]


def _tenant(kwargs):
    return get_object_or_404(Municipality, slug=kwargs["municipality_slug"], is_active=True)


class MunicipalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Municipality.objects.filter(is_active=True)
    serializer_class = MunicipalitySerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]


class FacilityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FacilitySerializer
    permission_classes = [permissions.AllowAny]
    lookup_value_converter = "int"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Facility.objects.none()
        return (
            Facility.objects.for_tenant(_tenant(self.kwargs))
            .filter(is_published=True)
            .select_related("parish")
            .prefetch_related("opening_hours", "tariffs")
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "week", OpenApiTypes.DATE, description="Calquera día da semana (ISO 8601)"
            )
        ],
        responses=SlotSerializer(many=True),
    )
    @action(detail=True)
    def availability(self, request, *args, **kwargs):
        facility = self.get_object()
        try:
            day = dt.date.fromisoformat(request.query_params.get("week", ""))
        except ValueError:
            day = timezone.localdate()
        monday = day - dt.timedelta(days=day.weekday())
        grid = booking_services.week_grid(facility, monday, request.user)
        slots = [s for _d, day_slots in grid["by_day"] for s in day_slots]
        return Response(
            SlotSerializer(
                [
                    {
                        "start": s.start,
                        "end": s.end,
                        "status": s.status,
                        "booked": s.booked,
                        "capacity": s.capacity,
                    }
                    for s in slots
                ],
                many=True,
            ).data
        )


class BookingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_value_converter = "int"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()
        return (
            Booking.objects.for_tenant(_tenant(self.kwargs))
            .filter(user=self.request.user)
            .select_related("facility")
        )

    @extend_schema(request=BookingCreateSerializer, responses={201: BookingSerializer})
    def create(self, request, *args, **kwargs):
        tenant = _tenant(self.kwargs)
        data = BookingCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        facility = get_object_or_404(
            Facility, municipality=tenant, pk=data.validated_data["facility"], is_published=True
        )
        rules = facility.current_rules()
        if not rules or rules.version != data.validated_data["accept_rules_version"]:
            return Response(
                {"detail": "Debes aceptar a versión vixente das normas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            booking = booking_services.create_booking(
                facility, data.validated_data["start"], request.user, rules_version=rules
            )
        except booking_services.BookingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=None,
        responses=inline_serializer(
            "CancelResult",
            {
                "refunded_cents": serializers.IntegerField(),
                "penalty_cents": serializers.IntegerField(),
            },
        ),
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        booking = self.get_object()
        try:
            refund, penalty = booking_services.cancel_booking(booking, by=request.user)
        except booking_services.BookingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"refunded_cents": refund, "penalty_cents": penalty})


class IncidentViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Incident.objects.none()
        return Incident.objects.for_tenant(_tenant(self.kwargs)).filter(reporter=self.request.user)

    def perform_create(self, serializer):
        tenant = _tenant(self.kwargs)
        facility = serializer.validated_data["facility"]
        if facility.municipality_id != tenant.pk:
            raise serializers.ValidationError({"facility": "Instalación doutro concello."})
        incident = serializer.save(municipality=tenant, reporter=self.request.user)
        notify_staff_new_incident(incident)
