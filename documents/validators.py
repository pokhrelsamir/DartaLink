import os

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED = {
    ".pdf": b"%PDF", ".png": b"\x89PNG", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff",
    ".doc": None, ".docx": b"PK", ".xls": None, ".xlsx": b"PK", ".txt": None, ".csv": None,
}


def validate_upload(f):
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in ALLOWED:
        raise ValidationError(f"'{f.name}': file type {ext or '(none)'} is not allowed. "
                              f"Allowed: {', '.join(sorted(ALLOWED))}.")
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    if f.size > limit:
        raise ValidationError(f"'{f.name}' is larger than {settings.MAX_UPLOAD_MB} MB.")
    if f.size == 0:
        raise ValidationError(f"'{f.name}' is empty.")
    magic = ALLOWED[ext]
    if magic:
        head = f.read(len(magic))
        f.seek(0)
        if not head.startswith(magic):
            raise ValidationError(f"'{f.name}' does not look like a valid {ext} file.")
