from django.urls import path

from . import views

app_name = "documents"
urlpatterns = [
    path("upload/<int:request_pk>/", views.upload, name="upload"),
    path("<int:pk>/view/", views.view, name="view"),
    path("<int:pk>/download/", views.download, name="download"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
