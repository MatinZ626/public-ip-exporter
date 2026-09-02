# Public IP Exporter

A lightweight Python Prometheus exporter for monitoring the **active public IPv4 address used by the server running Prometheus**.

This exporter is designed to run **on the same server as Prometheus** and is useful for servers with **multiple Internet links, gateways, or load-balanced WAN connections**, where you need to determine which public IP is currently being used for outbound traffic.

## How It Works

The exporter runs on the **same server where Prometheus is running**.

It sends an HTTP request to `icanhazip.com` and detects the public IPv4 address observed by the external service.

For example, if the Prometheus server has multiple Internet links:

```text
                    ┌── ISP 1 ── Public IP 1
Prometheus Server ──┤
                    └── ISP 2 ── Public IP 2
```

The exporter might return:

```text
server_public_ip{ip="Public IP 1"} 1
```

If the routing or load-balancing decision changes and the outbound traffic starts using the second link:

```text
server_public_ip{ip="Public IP 2"} 1
```

This allows Prometheus and Grafana to monitor which public IP is currently being used for outbound connectivity.

## Features

* Detects the active public IPv4 address
* Designed to run on the Prometheus server
* Useful for multiple Internet links and WAN failover monitoring
* Supports routing, NAT, and load-balanced environments
* Exposes a Prometheus-compatible `/metrics` endpoint
* Provides a human-readable `/status` endpoint
* Returns `0` when the public IP cannot be determined
* IPv6 addresses are ignored
* Runs as a non-root user inside Docker
* Lightweight and simple

## Prometheus Metric

The exporter exposes only one metric:

```text
server_public_ip
```

### Public IP Available

When a valid public IPv4 address is detected:

```text
server_public_ip{ip="Public IP 1"} 1
```

The `ip` label contains the currently detected public IPv4 address.

### Public IP Unavailable

If the exporter cannot retrieve or validate a public IPv4 address:

```text
server_public_ip 0
```

The metric uses `1` and `0` as boolean-like values:

* `1` → Public IPv4 is available
* `0` → Public IPv4 is unavailable

## Endpoints

### `/metrics`

Prometheus metrics endpoint.

Example:

```text
server_public_ip{ip="Public IP 1"} 1
```

### `/status`

Human-readable endpoint showing the currently detected public IPv4 address.

When available:

```text
Public IP 1
```

When unavailable:

```text
up link not available
```

### `/`

Basic application status endpoint.

Response:

```text
Public IP exporter is running
```

## Multiple Internet Links

This exporter is particularly useful when the Prometheus server has multiple outbound Internet links.

Example:

```text
                    ┌── ISP 1 ── Public IP 1
                    │
Prometheus ─ Router ┤
                    │
                    └── ISP 2 ── Public IP 2
```

The exporter determines the public IP **from the perspective of the external service**.

If routing, policy-based routing, NAT, failover, or load balancing changes the outbound path, the reported IP can change accordingly.

For example:

```text
09:00 → server_public_ip{ip="Public IP 1"} 1
09:05 → server_public_ip{ip="Public IP 1"} 1
09:10 → server_public_ip{ip="Public IP 2"} 1
```

This makes it possible to monitor WAN failover and outbound path changes through Prometheus and Grafana.

## Setup

The exporter is intended to run **on the same server as Prometheus**.

### 1. Build the Docker Image

Clone the repository and enter the project directory:

```bash
cd public-ip-exporter
```

Build the Docker image:

```bash
docker build -t public-ip-exporter:latest .
```

Verify the image:

```bash
docker images | grep public-ip-exporter
```

### 2. Run with Docker Compose

Create `docker-compose.yml`:

```yaml
services:
  public-ip-exporter:
    image: public-ip-exporter:latest
    container_name: public-ip-exporter
    restart: unless-stopped
    ports:
      - "127.0.0.1:9105:9105"
```

Start the exporter:

```bash
docker compose up -d
```

Check the container:

```bash
docker ps | grep public-ip-exporter
```

The exporter will be available locally on the Prometheus server at:

```text
http://127.0.0.1:9105
```

### 3. Test the Exporter

Check the application:

```bash
curl http://127.0.0.1:9105/
```

Expected response:

```text
Public IP exporter is running
```

Check the current public IP:

```bash
curl http://127.0.0.1:9105/status
```

Example:

```text
Public IP 1
```

Check Prometheus metrics:

```bash
curl http://127.0.0.1:9105/metrics
```

Example:

```text
server_public_ip{ip="Public IP 1"} 1
```

If the public IP is unavailable:

```text
server_public_ip 0
```

### 4. Configure Prometheus

Add the exporter to the existing `scrape_configs` section in `prometheus.yml`:

```yaml
scrape_configs:

  - job_name: "public-ip"
    static_configs:
      - targets:
          - "127.0.0.1:9105"
```

If Prometheus is running directly on the host, `127.0.0.1:9105` is the correct target.

If Prometheus is also running inside Docker on the same Docker network as the exporter, use the service name:

```yaml
scrape_configs:

  - job_name: "public-ip"
    static_configs:
      - targets:
          - "public-ip-exporter:9105"
```

After modifying the Prometheus configuration, reload or restart Prometheus.

### 5. Verify Prometheus

In the Prometheus UI, run:

```promql
server_public_ip
```

A successful result looks like:

```text
server_public_ip{ip="Public IP 1"} 1
```

To return only an available public IP:

```promql
server_public_ip == 1
```
## Important Note

The exporter detects the public IP used by **its own outbound HTTP request** to `icanhazip.com`.

Because the exporter runs on the same server as Prometheus, this normally represents the public IP of the Prometheus server's outbound connection.

However, if the network uses per-connection or per-flow load balancing, different requests may potentially leave through different Internet links.

Therefore, the detected IP represents the outbound path used for **that specific request**, rather than guaranteeing that every connection from the server uses the same public IP.

## Project Structure

```text
public-ip-exporter/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Requirements

* Docker
* Prometheus
* Internet connectivity from the exporter container
* Access to `icanhazip.com`

