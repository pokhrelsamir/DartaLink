"""Cisco branch-router reachability checker.

Run with ``python -m network_telemetry.router_checker`` from the backend root.
"""

import logging
import os
import platform
import re
import subprocess
import time

import django


logger = logging.getLogger(__name__)
RTT_PATTERN = re.compile(r"(?:time[=<]|Average = )\s*(\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE)


def _django_setup():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


def check_router(host="172.16.10.1", timeout_seconds=2):
    """Ping a router once and persist its reachability and measured RTT."""
    _django_setup()
    from .models import NetworkNodeStatus

    command = ["ping", "-n", "1", "-w", str(int(timeout_seconds * 1000)), host]
    if platform.system().lower() != "windows":
        command = ["ping", "-c", "1", "-W", str(max(1, int(timeout_seconds))), host]

    started = time.perf_counter()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds + 1,
                                check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        reachable = False
        output = str(exc)
    else:
        reachable = result.returncode == 0
        output = f"{result.stdout}\n{result.stderr}".strip()

    elapsed_ms = (time.perf_counter() - started) * 1000
    match = RTT_PATTERN.search(output)
    latency_ms = float(match.group(1).replace(",", ".")) if reachable and match else (
        round(elapsed_ms, 2) if reachable else None
    )
    status, _ = NetworkNodeStatus.objects.update_or_create(
        node_address=host,
        defaults={
            "node_name": "Cisco branch router",
            "is_reachable": reachable,
            "latency_ms": latency_ms,
            "error_message": "" if reachable else output[:255],
        },
    )
    logger.info("Router %s is %s%s", host, "reachable" if reachable else "unreachable",
                f" ({latency_ms:.2f} ms)" if latency_ms is not None else "")
    return status


def run_forever(interval_seconds=60, host="172.16.10.1"):
    while True:
        check_router(host)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("DARTALINK_TELEMETRY_LOG_LEVEL", "INFO"))
    run_forever(
        interval_seconds=int(os.getenv("DARTALINK_ROUTER_CHECK_INTERVAL", "60")),
        host=os.getenv("DARTALINK_ROUTER_HOST", "172.16.10.1"),
    )
