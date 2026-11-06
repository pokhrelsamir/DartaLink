from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("requests_app", "0004_administrativerequest_branch_verified_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="administrativerequest",
            name="customer_contact",
            field=models.CharField(blank=True, max_length=10),
        ),
    ]
