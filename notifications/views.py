from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from requests_app.selectors import visible_requests

from .forms import DirectMessageForm
from .models import DirectMessage, Notification
from .services import send_direct_message


@login_required
def notification_list(request):
    qs = Notification.objects.filter(recipient=request.user).select_related("request")
    only_unread = request.GET.get("filter") == "unread"
    if only_unread:
        qs = qs.filter(is_read=False)
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {
        "page": page, "only_unread": only_unread, "breadcrumbs": [("Notifications", "")],
        "messages_page": DirectMessage.objects.filter(recipient=request.user),
    })


@login_required
def direct_message_create(request):
    if not request.user.is_sysadmin:
        raise PermissionDenied
    form = DirectMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        department = form.cleaned_data["department"]
        if form.cleaned_data["recipient_mode"] == "all":
            recipients = department.members.filter(is_active=True).order_by("staff_id")
        else:
            recipients = form.cleaned_data["recipients"]
        for recipient in recipients:
            send_direct_message(request.user, recipient, form.cleaned_data["subject"], form.cleaned_data["body"])
        messages.success(request, f"Message sent to {len(recipients)} employee(s).")
        return redirect("notifications:list")
    return render(request, "notifications/direct_message_form.html", {
        "form": form, "breadcrumbs": [("Notifications", reverse("notifications:list")), ("Send message", "")],
    })


@login_required
def open_notification(request, pk):
    n = get_object_or_404(
        Notification.objects.select_related("direct_message", "direct_message__sender"),
        pk=pk,
        recipient=request.user,
    )
    direct_message = n.direct_message
    if direct_message is None and not n.request_id:
        direct_message = DirectMessage.objects.select_related("sender").filter(
            recipient=request.user,
            subject=n.title,
        ).filter(
            created_at__lte=n.created_at,
        ).order_by("-created_at", "-id").first()
        if direct_message and n.message != (
            f"From {direct_message.sender.display_name}: {direct_message.body}"
        )[:300]:
            direct_message = None
        if direct_message:
            n.direct_message = direct_message
            n.save(update_fields=["direct_message"])
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    if direct_message:
        return render(request, "notifications/direct_message_detail.html", {
            "message": direct_message,
            "breadcrumbs": [("Notifications", reverse("notifications:list")), (n.title, "")],
        })
    if n.request_id and visible_requests(request.user).filter(pk=n.request_id).exists():
        return redirect(n.request.get_absolute_url())
    return redirect("notifications:list")


@login_required
@require_POST
def mark_read(request, pk):
    Notification.objects.filter(pk=pk, recipient=request.user).update(is_read=True)
    return redirect(request.POST.get("next") or "notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"unread": 0})
    return redirect(request.POST.get("next") or "notifications:list")


@login_required
@require_GET
def unread_count(request):
    return JsonResponse({"unread": Notification.objects.filter(recipient=request.user, is_read=False).count()})
