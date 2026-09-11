from django.urls import path

from .views import (
    login_view,
    portal_view,
    camera_capture_view,
    darta_entry_view,
    chalani_entry_view,
    create_darta_api,
    upload_document_api,
)


urlpatterns = [
    # Page routes
    path(
        "login/",
        login_view,
        name="login"
    ),

    path(
        "portal/",
        portal_view,
        name="portal"
    ),

    path(
        "camera-capture/",
        camera_capture_view,
        name="camera_capture"
    ),

    path(
        "darta-entry/",
        darta_entry_view,
        name="darta_entry"
    ),

    path(
        "chalani-entry/",
        chalani_entry_view,
        name="chalani_entry"
    ),

    # Darta API
    path(
        "api/darta/create/",
        create_darta_api,
        name="create_darta_api"
    ),

    # Document upload API
    path(
        "api/documents/upload/",
        upload_document_api,
        name="upload_document_api"
    ),
]