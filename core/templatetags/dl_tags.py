from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

_ICONS = {
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
    "inbox": '<path d="M3 13l3-8h12l3 8"/><path d="M3 13v6h18v-6h-5l-1 3H9l-1-3z"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 13h6M9 17h6"/>',
    "bolt": '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "bell": '<path d="M6 16V11a6 6 0 0112 0v5l2 2H4z"/><path d="M10 21h4"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c.8-3.5 3.3-5 7-5s6.2 1.5 7 5"/><path d="M16 4.5a3.5 3.5 0 010 7M18 15c2.200.6 3.500 2.200 4 5"/>',
    "building": '<path d="M4 21V4h10v17"/><path d="M14 9h6v12"/><path d="M8 8h2M8 12h2M8 16h2"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "code": '<path d="M8 8l-5 4 5 4M16 8l5 4-5 4M14 5l-4 14"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
    "key": '<circle cx="17" cy="7" r="3.2"/><path d="M14.7 9.3L4 20M7.5 16.5l2 2M5.5 18.5l2 2"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "logout": '<path d="M9 4H5v16h4"/><path d="M16 8l4 4-4 4M20 12H9"/>',
    "check": '<path d="M5 12l5 5 9-10"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 20h16"/>',
    "download": '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 20h16"/>',
    "eye": '<path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6z"/><circle cx="12" cy="12" r="2.5"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
    "edit": '<path d="M4 20l1-5L16 4l4 4L9 19z"/>',
    "pencil-down-left": '<path d="M20 4L4 20"/><path d="M4 20l1-5 4 4-5 1z"/><path d="M14 6l4 4"/>',
    "trash": '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "chevron": '<path d="M9 6l6 6-6 6"/>',
}


@register.simple_tag
def icon(name, size=18):
    body = _ICONS.get(name, "")
    return format_html(
        '<svg class="icon" width="{0}" height="{0}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{1}</svg>',
        size, mark_safe(body))


@register.simple_tag
def status_badge(req):
    return format_html('<span class="badge badge-{}">{}</span>', req.badge_class, req.get_status_display())


@register.simple_tag
def priority_badge(req):
    tone = {"LOW": "neutral", "NORMAL": "neutral", "HIGH": "warn", "URGENT": "danger"}.get(req.priority, "neutral")
    return format_html('<span class="badge badge-{} badge-soft">{}</span>', tone, req.get_priority_display())


@register.simple_tag(takes_context=True)
def page_url(context, number):
    params = context["request"].GET.copy()
    params["page"] = number
    return "?" + params.urlencode()


@register.filter
def filesize(value):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


@register.filter
def action_label(key):
    return {
        "create": "Draft created", "edit": "Details edited", "submit": "Submitted", "verify": "Verified",
        "register": "Registered in Darta", "forward": "Forwarded", "recommend": "Recommendation added",
        "tippani": "Tippani added", "tok_aadesh": "Tok Aadesh issued", "approve": "Approved",
        "reject": "Rejected", "return": "Returned for revision", "process": "Processing started",
        "dispatch": "Dispatched (Chalani)", "complete": "Completed", "cancel": "Cancelled",
    }.get(key, key.replace("_", " ").capitalize())


@register.filter
def action_tone(key):
    return {"approve": "ok", "verify": "ok", "dispatch": "ok", "complete": "ok", "register": "ok",
            "reject": "danger", "cancel": "danger", "return": "warn", "tok_aadesh": "warn"}.get(key, "info")
