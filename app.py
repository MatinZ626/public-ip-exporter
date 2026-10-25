import ipaddress
import logging
import threading
import time

import requests
from flask import Flask, Response

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("public-ip-exporter")

CHECK_INTERVAL = 60

REQUEST_TIMEOUT = (3, 5)

IP_PROVIDERS = [
    ("aws", "https://checkip.amazonaws.com"),
    ("icanhazip", "https://ipv4.icanhazip.com"),
    ("ipify", "https://api.ipify.org"),
]

state_lock = threading.Lock()

state = {
    "ip": None,
    "lookup_success": 0,
    "last_success_timestamp": 0,
    "last_check_timestamp": 0,
}


def get_public_ip():
    """Return the first valid public IPv4 from available providers."""

    for provider, url in IP_PROVIDERS:
        try:
            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            ip = ipaddress.ip_address(response.text.strip())

            if not isinstance(ip, ipaddress.IPv4Address):
                raise ValueError("Provider did not return IPv4")

            if not ip.is_global:
                raise ValueError("Provider did not return a global IPv4")

            logger.info(
                "Public IP retrieved from %s: %s",
                provider,
                ip,
            )
            return str(ip)

        except (requests.RequestException, ValueError) as exc:
            logger.warning(
                "Provider %s failed (%s): %s",
                provider,
                type(exc).__name__,
                exc,
            )

    logger.error("All public IP providers failed")
    return None


def refresh_public_ip():
    """Perform one lookup and update the cached state."""

    ip = get_public_ip()
    now = time.time()

    with state_lock:
        state["last_check_timestamp"] = now
        state["lookup_success"] = 1 if ip else 0

        if ip:
            state["ip"] = ip
            state["last_success_timestamp"] = now
            logger.info("Cached public IP updated: %s", ip)
        else:
            # Preserve the last known valid IP.
            logger.error(
                "Lookup failed; preserving last known IP: %s",
                state["ip"],
            )


def refresh_loop():
    """Refresh the cached IP periodically in the background."""

    while True:
        try:
            refresh_public_ip()
        except Exception:
            logger.exception("Unexpected error during IP refresh")

        time.sleep(CHECK_INTERVAL)


@app.route("/metrics")
def metrics():
    # This endpoint never calls an external IP provider.
    with state_lock:
        ip = state["ip"]
        success = state["lookup_success"]
        last_success = state["last_success_timestamp"]
        last_check = state["last_check_timestamp"]

    lines = [
        "# HELP server_public_ip Current or last known public IPv4.",
        "# TYPE server_public_ip gauge",
    ]

    if ip:
        lines.append(f'server_public_ip{{ip="{ip}"}} 1')
    else:
        lines.append("server_public_ip 0")

    lines.extend([
        "# HELP server_public_ip_lookup_success Whether the latest lookup succeeded.",
        "# TYPE server_public_ip_lookup_success gauge",
        f"server_public_ip_lookup_success {success}",
        "# HELP server_public_ip_last_success_timestamp_seconds Unix timestamp of last successful lookup.",
        "# TYPE server_public_ip_last_success_timestamp_seconds gauge",
        f"server_public_ip_last_success_timestamp_seconds {last_success}",
        "# HELP server_public_ip_last_check_timestamp_seconds Unix timestamp of last lookup attempt.",
        "# TYPE server_public_ip_last_check_timestamp_seconds gauge",
        f"server_public_ip_last_check_timestamp_seconds {last_check}",
    ])

    return Response(
        "\n".join(lines) + "\n",
        mimetype="text/plain; version=0.0.4; charset=utf-8",
    )


@app.route("/status")
def status():
    with state_lock:
        ip = state["ip"]
        success = state["lookup_success"]

    if ip and success:
        return Response(f"OK: {ip}\n", mimetype="text/plain")

    if ip:
        return Response(
            f"WARNING: last known IP is {ip}, latest lookup failed\n",
            mimetype="text/plain",
            status=503,
        )

    return Response(
        "ERROR: no public IP available yet\n",
        mimetype="text/plain",
        status=503,
    )


@app.route("/")
def index():
    return "Public IP exporter is running\n"


# Start one background refresh loop when this process imports the app.
refresh_thread = threading.Thread(
    target=refresh_loop,
    name="public-ip-refresh",
    daemon=True,
)
refresh_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9105)
