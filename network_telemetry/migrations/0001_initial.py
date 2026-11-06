from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="NetworkAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("source_address", models.GenericIPAddressField()),
                ("source_port", models.PositiveIntegerField()),
                ("facility", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("severity", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("message", models.TextField()),
                ("event_type", models.CharField(db_index=True, max_length=40)),
            ],
            options={"ordering": ["-received_at"]},
        ),
        migrations.CreateModel(
            name="NetworkNodeStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("node_address", models.GenericIPAddressField(unique=True)),
                ("node_name", models.CharField(blank=True, max_length=100)),
                ("is_reachable", models.BooleanField()),
                ("latency_ms", models.FloatField(blank=True, null=True)),
                ("checked_at", models.DateTimeField(auto_now=True)),
                ("error_message", models.CharField(blank=True, max_length=255)),
            ],
            options={"ordering": ["node_address"]},
        ),
    ]
