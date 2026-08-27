from django.shortcuts import render


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