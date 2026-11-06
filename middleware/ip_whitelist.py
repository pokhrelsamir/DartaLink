import ipaddress
import logging
import re

from django.conf import settings
from django.db import DatabaseError
from django.http import HttpResponseForbidden


logger = logging.getLogger("dartalink.security")

DEFAULT_ALLOWED_IPS = frozenset(
    {"127.0.0.1", "192.168.10.10", "192.168.10.11", "192.168.10.12",
     "192.168.10.13", "192.168.10.14", "192.168.10.15"}
)
DISPATCH_PATH = re.compile(r"^/requests/\d+/action/dispatch/?$")


def _allowed_addresses():
    configured = getattr(settings, "DARTALINK_DISPATCH_ALLOWED_IPS", DEFAULT_ALLOWED_IPS)
    return frozenset(ipaddress.ip_address(address) for address in configured)


class DispatchIPWhitelistMiddleware:
    """Restrict the state-changing Chalani dispatch action to trusted hosts."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_addresses = _allowed_addresses()

    def __call__(self, request):
        if DISPATCH_PATH.fullmatch(request.path_info):
            client_ip = request.META.get("REMOTE_ADDR", "")
            try:
                authorized = ipaddress.ip_address(client_ip) in self.allowed_addresses
            except ValueError:
                authorized = False

            if not authorized:
                audit_address = client_ip
                try:
                    ipaddress.ip_address(audit_address)
                except ValueError:
                    audit_address = "0.0.0.0"
                logger.warning(
                    "Blocked unauthorized dispatch request from %s: %s %s",
                    client_ip or "<unknown>",
                    request.method,
                    request.get_full_path(),
                )
                try:
                    from network_telemetry.models import NetworkAuditLog

                    NetworkAuditLog.objects.create(
                        source_address=audit_address,
                        source_port=0,
                        message=(
                            f"Blocked {request.method} request to "
                            f"{request.get_full_path()} from unauthorized client."
                        ),
                        event_type="IP_WHITELIST_DENIED",
                    )
                except DatabaseError:
                    logger.exception("Unable to persist dispatch IP whitelist audit event.")
                return HttpResponseForbidden("Dispatch access is restricted to authorized devices.")

        return self.get_response(request)
