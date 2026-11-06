from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save

DEFAULT_DEPARTMENTS = [
    # code, name, name_np, authority, registry
    ("KP", "Karyalaya Pramukh", "कार्यालय प्रमुख", True, False),
    ("PP", "Prabidhik Pramukh", "प्राविधिक प्रमुख", True, False),
    ("LP", "Lekha Pramukh", "लेखा प्रमुख", True, False),
    ("RS", "Rajaswa Sakha", "राजस्व शाखा", True, False),
    ("BS", "Budget Sakha", "बजेट शाखा", True, False),
    ("IT", "IT Sakha", "आईटी शाखा", True, False),
    ("DT", "Darta", "दर्ता", False, True),
    ("CH", "Chalani", "चलानी", False, True),
]


def create_default_departments(sender, **kwargs):
    from .models import Department
    for code, name, name_np, authority, registry in DEFAULT_DEPARTMENTS:
        Department.objects.get_or_create(
            code=code,
            defaults={"name": name, "name_np": name_np, "is_authority": authority, "is_registry": registry},
        )


def create_profile(sender, instance, created, **kwargs):
    from .models import StaffProfile
    if created:
        StaffProfile.objects.get_or_create(user=instance)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        from django.contrib.auth import get_user_model
        post_migrate.connect(create_default_departments, sender=self)
        post_save.connect(create_profile, sender=get_user_model(), dispatch_uid="dl_create_profile")
