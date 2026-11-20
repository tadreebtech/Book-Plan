from django.db import migrations, models


def populate_moderation_status(apps, schema_editor):
    resource = apps.get_model("bookings", "Resource")
    resource.objects.using(schema_editor.connection.alias).filter(moderation_status="PENDING").update(
        moderation_status=models.Case(
            models.When(is_active=True, then=models.Value("APPROVED")),
            default=models.Value("HIDDEN"),
        )
    )


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0002_resource_moderation"),
    ]

    operations = [
        migrations.RunPython(populate_moderation_status, migrations.RunPython.noop),
    ]
