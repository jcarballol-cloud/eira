# SPDX-License-Identifier: EUPL-1.2
"""Os apelidos pasan de estar na conta/menor a ser un dato da inscrición (minimización)."""

from django.db import migrations


def copy(apps, schema_editor):
    Enrollment = apps.get_model("activities", "Enrollment")
    for e in Enrollment.objects.select_related("user", "dependent").all():
        source = e.dependent if e.dependent_id else e.user
        value = getattr(source, "surnames", "") if source else ""
        if value and not e.surnames:
            e.surnames = value
            e.save(update_fields=["surnames"])


class Migration(migrations.Migration):
    dependencies = [
        ("activities", "0004_v3_enrollment_surnames"),
        ("accounts", "0006_v3_kiosk"),
    ]
    operations = [migrations.RunPython(copy, migrations.RunPython.noop)]
