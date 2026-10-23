# SPDX-License-Identifier: EUPL-1.2
"""Exportación iCalendar (RFC 5545) e ligazón «engadir a Google Calendar»."""

import datetime as dt
from urllib.parse import urlencode


def _fmt(value):
    return value.astimezone(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def _escape(text):
    return (
        str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )


def _fold(line):
    """Pregado de liñas a 75 octetos (RFC 5545 §3.1)."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > (75 if not parts else 74):
            parts.append(current.decode("utf-8"))
            current = b""
        current += b
    parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def event_lines(booking, url=""):
    f = booking.facility
    location = ", ".join(x for x in [f.name, f.address, booking.municipality.name] if x)
    lines = [
        "BEGIN:VEVENT",
        f"UID:{booking.reference}@{booking.municipality.slug}.eira",
        f"DTSTAMP:{_fmt(booking.created_at)}",
        f"DTSTART:{_fmt(booking.start)}",
        f"DTEND:{_fmt(booking.end)}",
        f"SUMMARY:{_escape(f.name)}",
        f"LOCATION:{_escape(location)}",
        f"DESCRIPTION:{_escape('Reserva ' + booking.reference + (chr(10) + url if url else ''))}",
        "STATUS:" + ("CANCELLED" if booking.status == "cancelled" else "CONFIRMED"),
    ]
    if f.latitude is not None and f.longitude is not None:
        lines.append(f"GEO:{f.latitude};{f.longitude}")
    if url:
        lines.append(f"URL:{url}")
    lines.append("END:VEVENT")
    return lines


def calendar(bookings, url_for=None, name="Eira"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Equipo Eira//Eira//GL",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
    ]
    for b in bookings:
        lines.extend(event_lines(b, url_for(b) if url_for else ""))
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def google_calendar_url(booking, url=""):
    f = booking.facility
    params = {
        "action": "TEMPLATE",
        "text": f.name,
        "dates": f"{_fmt(booking.start)}/{_fmt(booking.end)}",
        "details": f"Reserva {booking.reference}\n{url}".strip(),
        "location": ", ".join(x for x in [f.name, f.address, booking.municipality.name] if x),
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)
