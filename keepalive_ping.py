from __future__ import annotations

import argparse
import sys
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


DEFAULT_URL = "https://gt7-weather-draw-web-1wmp.onrender.com/keepalive"


def ping(url: str, timeout: int = 10) -> int:
    request = Request(
        url,
        headers={
            "User-Agent": "GT7-Keepalive/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"HTTP {response.status}")
            if body.strip():
                print(body.strip())
            return 0
    except HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        return 1
    except URLError as exc:
        print(f"Network error: {exc.reason}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Ping Render keepalive endpoint.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Keepalive URL to ping")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="How many pings to send before exiting",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        help="Seconds between pings when repeating",
    )
    args = parser.parse_args()

    for index in range(args.repeat):
        print(f"Ping {index + 1}/{args.repeat}: {args.url}")
        exit_code = ping(args.url)
        if exit_code != 0:
            return exit_code
        if index + 1 < args.repeat:
            time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
