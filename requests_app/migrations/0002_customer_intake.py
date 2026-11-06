from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("requests_app", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="administrativerequest",
            name="customer_name",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="administrativerequest",
            name="customer_contact",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="administrativerequest",
            name="intake_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="requests_intaken",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
