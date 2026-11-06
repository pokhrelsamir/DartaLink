"""UDP syslog listener for Cisco link-state events.

Run with ``python -m network_telemetry.syslog_listener`` from the backend root.
"""

import logging
import os
import re
import socket
from contextlib import closing

import django


logger = logging.getLogger(__name__)
EVENT_TYPES = ("LINK-3-UPDOWN", "LINEPROTO-5-UPDOWN")
EVENT_PATTERN = re.compile("|".join(re.escape(event) for event in EVENT_TYPES))


def _django_setup():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


def _parse_syslog(message):
    priority = re.search(r"<(\d+)>", message)
    if not priority:
        return None, None
    value = int(priority.group(1))
    return value // 8, value % 8


def serve_forever(host="0.0.0.0", port=514, buffer_size=8192):
    """Receive Cisco syslog datagrams and persist only supported link events."""
    _django_setup()
    from .models import NetworkAuditLog

    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        logger.info("Cisco syslog listener bound to %s:%s", host, port)
        while True:
            payload, address = listener.recvfrom(buffer_size)
            message = payload.decode("utf-8", errors="replace").strip()
            match = EVENT_PATTERN.search(message)
            if not match:
                continue
            facility, severity = _parse_syslog(message)
            NetworkAuditLog.objects.create(
                source_address=address[0],
                source_port=address[1],
                facility=facility,
                severity=severity,
                message=message,
                event_type=match.group(0),
            )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("DARTALINK_TELEMETRY_LOG_LEVEL", "INFO"))
    serve_forever(
        host=os.getenv("DARTALINK_SYSLOG_HOST", "0.0.0.0"),
        port=int(os.getenv("DARTALINK_SYSLOG_PORT", "514")),
    )
