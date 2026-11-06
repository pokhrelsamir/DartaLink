import datetime

from django.utils import timezone


def fiscal_year_label(date=None):
    """Approximate Nepali fiscal year label (starts Shrawan 1, ~17 July): 2083/84."""
    date = date or timezone.localdate()
    start_bs = date.year + 57 if (date.month, date.day) >= (7, 17) else date.year + 56
    return f"{start_bs}/{(start_bs + 1) % 100:02d}"


def today():
    return timezone.localdate()
