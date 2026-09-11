from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Document, DartaEntry
from .serializers import DartaEntrySerializer


def login_view(request):

    return render(
        request,
        "login.html"
    )


def portal_view(request):

    return render(
        request,
        "portal.html"
    )


def camera_capture_view(request):

    return render(
        request,
        "camera-capture.html"
    )


def darta_entry_view(request):

    return render(
        request,
        "darta-entry.html"
    )


def chalani_entry_view(request):

    return render(
        request,
        "chalani-entry.html"
    )


# -----------------------------------------
# Darta Creation API
# -----------------------------------------

@api_view(["POST"])
def create_darta_api(request):

    serializer = DartaEntrySerializer(
        data=request.data,
        context={
            "request": request
        }
    )

    if serializer.is_valid():

        darta_entry = serializer.save()

        return Response(
            DartaEntrySerializer(
                darta_entry,
                context={
                    "request": request
                }
            ).data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


# -----------------------------------------
# Supabase Storage Upload API
# September 11, 2026
# -----------------------------------------

@require_POST
def upload_document_api(request):

    uploaded_file = request.FILES.get("document")

    if not uploaded_file:

        return JsonResponse(
            {
                "success": False,
                "message": "No document file was provided."
            },
            status=400
        )


    # Allowed document types

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }

    if uploaded_file.content_type not in allowed_types:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Only JPG, PNG, WEBP and PDF files "
                    "are allowed."
                )
            },
            status=400
        )


    # Maximum file size: 10 MB

    max_size = 10 * 1024 * 1024

    if uploaded_file.size > max_size:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "The document must be smaller "
                    "than 10 MB."
                )
            },
            status=400
        )


    supabase_url = getattr(
        settings,
        "SUPABASE_URL",
        ""
    )

    service_role_key = getattr(
        settings,
        "SUPABASE_SERVICE_ROLE_KEY",
        ""

    )

    bucket = getattr(
        settings,
        "SUPABASE_STORAGE_BUCKET",
        "dartalink-documents"
    )


    if not supabase_url or not service_role_key:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Supabase Storage is not configured. "
                    "Please check the server environment variables."
                )
            },
            status=503
        )


    # Keep only the original filename, not its path

    original_name = Path(
        uploaded_file.name
    ).name

    extension = Path(
        original_name
    ).suffix.lower()


    # Generate a unique storage path

    storage_name = (
        f"documents/"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )


    encoded_bucket = quote(
        bucket,
        safe=""
    )

    encoded_path = quote(
        storage_name,
        safe="/"
    )


    upload_url = (
        f"{supabase_url}"
        f"/storage/v1/object/"
        f"{encoded_bucket}/"
        f"{encoded_path}"
    )


    try:

        file_content = uploaded_file.read()

        request_headers = {
            "Authorization":
                f"Bearer {service_role_key}",

            "apikey":
                service_role_key,

            "Content-Type":
                uploaded_file.content_type,

            "x-upsert":
                "false",
        }


        upload_request = Request(
            upload_url,
            data=file_content,
            headers=request_headers,
            method="POST"
        )


        with urlopen(
            upload_request,
            timeout=30
        ) as response:

            response_body = response.read().decode(
                "utf-8"
            )


    except HTTPError as error:

        error_body = ""

        try:
            error_body = error.read().decode(
                "utf-8"
            )
        except Exception:
            pass

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Cloud storage upload failed."
                ),
                "details": error_body
            },
            status=502
        )


    except URLError as error:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Unable to connect to Supabase Storage."
                ),
                "details": str(error.reason)
            },
            status=502
        )


    except Exception as error:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Unexpected error during "
                    "cloud storage upload."
                ),
                "details": str(error)
            },
            status=500
        )


    # Public URL is useful when the bucket is public.
    # For a private bucket, the storage path is still returned.

    public_url = (
        f"{supabase_url}"
        f"/storage/v1/object/public/"
        f"{encoded_bucket}/"
        f"{encoded_path}"
    )


    return JsonResponse(
        {
            "success": True,
            "message": "Document uploaded successfully.",
            "file_name": original_name,
            "storage_path": storage_name,
            "file_url": public_url,
            "supabase_response": response_body,
        },
        status=201
    )