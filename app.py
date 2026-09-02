from flask import Flask, Response
import requests
import ipaddress

app = Flask(__name__)


def get_public_ip():
    try:
        response = requests.get(
            "https://icanhazip.com",
            timeout=5
        )

        response.raise_for_status()

        ip = response.text.strip()

        # فقط IPv4 معتبر
        parsed_ip = ipaddress.ip_address(ip)

        if parsed_ip.version != 4:
            return None

        return ip

    except Exception:
        return None


@app.route("/metrics")
def metrics():
    ip = get_public_ip()

    if ip:
        return Response(
            f'server_public_ip{{ip="{ip}"}} 1\n',
            mimetype="text/plain"
        )

    return Response(
        "server_public_ip 0\n",
        mimetype="text/plain"
    )


@app.route("/status")
def status():
    ip = get_public_ip()

    if ip:
        return Response(
            f"{ip}\n",
            mimetype="text/plain"
        )

    return Response(
        "up link not available\n",
        mimetype="text/plain"
    )


@app.route("/")
def index():
    return "Public IP exporter is running\n"


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=9105
    )
