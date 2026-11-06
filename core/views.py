from django.http import HttpResponse
from django.template.loader import render_to_string


def _page(template, status):
    # rendered without the request/context processors so error pages never fail themselves
    return HttpResponse(render_to_string(template), status=status)


def error_400(request, exception=None):
    return _page("errors/400.html", 400)


def error_403(request, exception=None):
    return _page("errors/403.html", 403)


def error_404(request, exception=None):
    return _page("errors/404.html", 404)


def error_500(request):
    return _page("errors/500.html", 500)
