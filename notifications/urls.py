from django.urls import path

from . import views

app_name = "notifications"
urlpatterns = [
    path("", views.notification_list, name="list"),
    path("send/", views.direct_message_create, name="send"),
    path("unread-count/", views.unread_count, name="unread_count"),
    path("read-all/", views.mark_all_read, name="mark_all_read"),
    path("<int:pk>/open/", views.open_notification, name="open"),
    path("<int:pk>/read/", views.mark_read, name="mark_read"),
]
