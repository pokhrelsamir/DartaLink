from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_directmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="direct_message",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="notifications.directmessage",
            ),
        ),
    ]
