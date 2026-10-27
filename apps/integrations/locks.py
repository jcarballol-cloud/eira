# SPDX-License-Identifier: EUPL-1.2
"""Pechaduras conectadas (nivel 3) e control de luces detrás dun adaptador."""

from .models import OutboundMessage


class LockAdapter:
    def open(self, device, booking=None):
        raise NotImplementedError

    def set_lights(self, device, on, until=None):
        raise NotImplementedError

    def door_state(self, device):
        """v1.2: "closed", "open" ou "" se a pechadura non informa do estado da porta."""
        raise NotImplementedError


class MockConnectedLockAdapter(LockAdapter):
    """Simula un broker MQTT: publica a orde en `eira/<concello>/<dispositivo>/cmd`."""

    def _publish(self, device, payload):
        topic = f"eira/{device.municipality.slug}/{device.pk}/cmd"
        OutboundMessage.objects.create(channel="mqtt", target=topic, payload=payload)
        return True

    def open(self, device, booking=None):
        return self._publish(
            device, {"cmd": "open", "booking": getattr(booking, "reference", None)}
        )

    def set_lights(self, device, on, until=None):
        return self._publish(
            device, {"cmd": "lights", "on": on, "until": until.isoformat() if until else None}
        )

    def door_state(self, device):
        # O simulador de pechadura (/dev/lock-simulator/) garda o estado no dispositivo
        if device.door_closed is None:
            return ""
        return "closed" if device.door_closed else "open"


class HttpLockAdapter(LockAdapter):
    """Esqueleto: pechadura con API HTTP local (pasarela na instalación con TLS mutuo)."""

    def open(self, device, booking=None):
        raise NotImplementedError

    def set_lights(self, device, on, until=None):
        raise NotImplementedError
