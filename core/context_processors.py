from django.conf import settings
from django.contrib import messages as dj_messages
from django.urls import reverse

from notifications.models import Notification


def _item(label, url, icon, **extra):
    return {"label": label, "url": url, "path": url.split("?")[0], "icon": icon, **extra}


def build_nav(user):
    groups = [{"title": "", "items": [_item("Dashboard", reverse("dashboard:home"), "home")]}]
    req_items = [_item("All requests", reverse("requests:list"), "inbox", key="all")]
    if user.can_create_requests:
        req_items.append(_item("My requests", reverse("requests:list") + "?scope=mine", "file", scope="mine"))
    if not user.is_sysadmin:
        req_items.append(_item("Needs my action", reverse("requests:list") + "?scope=action", "bolt", scope="action"))
    if user.can_create_requests:
        req_items.append(_item("New request", reverse("requests:create"), "plus", key="new"))
    groups.append({"title": "Requests", "items": req_items})
    groups.append({"title": "Account", "items": [
        _item("Notifications", reverse("notifications:list"), "bell", key="notifications"),
        _item("My profile", reverse("accounts:profile"), "user"),
    ]})
    if user.is_sysadmin:
        groups.append({"title": "Administration", "items": [
            _item("Send message", reverse("notifications:send"), "mail"),
            _item("Users", reverse("accounts:user_list"), "users"),
            _item("Departments", reverse("accounts:department_list"), "building"),
            _item("Audit log", reverse("workflow:audit"), "clock"),
            _item("API docs", "/api/docs/", "code", external=True),
            _item("Django admin", "/admin/", "settings", external=True),
        ]})
    return groups


def _is_active(item, request):
    path, scope = request.path, request.GET.get("scope", "")
    if item.get("external"):
        return False
    if item.get("key") == "all":
        return path.startswith("/requests/") and not path.startswith("/requests/new") and scope not in ("mine", "action")
    if item.get("key") == "new":
        return path.startswith("/requests/new")
    if item.get("key") == "notifications":
        return path.startswith(item["path"]) and path != reverse("notifications:send")
    if "scope" in item:
        return path == item["path"] and scope == item["scope"]
    if item["path"] == "/":
        return path == "/"
    return path.startswith(item["path"])


def shell(request):
    ctx = {"BRAND_LOGO": settings.BRAND_LOGO}
    if hasattr(request, "_messages"):
        ctx["messages_json"] = [{"message": str(m.message), "tags": m.tags} for m in dj_messages.get_messages(request)]
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        groups = build_nav(user)
        for g in groups:
            for it in g["items"]:
                it["active"] = _is_active(it, request)
        ctx["nav_groups"] = groups
        ctx["unread_count"] = Notification.objects.filter(recipient=user, is_read=False).count()
        ctx["recent_notifications"] = list(Notification.objects.filter(recipient=user)[:6])
    return ctx
