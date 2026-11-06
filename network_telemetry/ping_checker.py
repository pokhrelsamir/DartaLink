"""OS-level live RTT checks for dashboard clients and network nodes."""

import ipaddress
import platform
import re
import subprocess
import time


RTT_PATTERN = re.compile(r"(?:time[=<]|Average = )\s*(\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE)


def ping_host(host, timeout_seconds=2):
    """Return reachability and RTT for a validated IPv4/IPv6 address.

    The address is validated before being passed as a subprocess argument so
    request-derived values cannot become shell input.
    """
    address = ipaddress.ip_address(host)
    timeout_ms = max(1, int(timeout_seconds * 1000))
    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", str(timeout_ms), str(address)]
    else:
        command = ["ping", "-c", "1", "-W", str(max(1, int(timeout_seconds))), str(address)]

    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 1,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"host": str(address), "reachable": False, "latency_ms": None, "error": str(exc)}

    output = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode != 0:
        return {"host": str(address), "reachable": False, "latency_ms": None, "error": output[:255]}

    match = RTT_PATTERN.search(output)
    latency_ms = float(match.group(1).replace(",", ".")) if match else round(
        (time.perf_counter() - started) * 1000, 2
    )
    return {"host": str(address), "reachable": True, "latency_ms": latency_ms, "error": ""}


def client_ping(request, timeout_seconds=2):
    """Measure the current request client's network RTT."""
    client_ip = request.META.get("REMOTE_ADDR", "")
    return ping_host(client_ip, timeout_seconds=timeout_seconds)
