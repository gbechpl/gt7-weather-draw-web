from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from draw_core import ALL_WEATHER, PROFILES, generate_weather_slots


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
PROFILE_LABELS = {
    "dry": "Suchy",
    "equal": "Zrównoważony",
    "mixed": "Mieszany",
    "wet": "Mokry",
}


def parse_unique_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    raise ValueError("invalid_unique")


@app.get("/")
def index():
    profile_options = [
        {"value": key, "label": PROFILE_LABELS.get(key, key)}
        for key in sorted(PROFILES.keys())
    ]
    return render_template(
        "index.html",
        profiles=profile_options,
        weather_count=len(ALL_WEATHER),
    )


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/draw")
def api_draw():
    payload = request.get_json(silent=True) or {}

    try:
        slot_count = int(payload.get("slot_count", 9))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_slot_count"}), 400
    if slot_count < 3 or slot_count > 9:
        return jsonify({"error": "invalid_slot_count_range", "min": 3, "max": 9}), 400

    profile = str(payload.get("profile", "mixed")).strip().lower() or "mixed"
    if profile not in PROFILES:
        return jsonify({"error": "invalid_profile", "profiles": sorted(PROFILES.keys())}), 400

    try:
        unique = parse_unique_flag(payload.get("unique", False))
    except ValueError:
        return jsonify({"error": "invalid_unique"}), 400

    try:
        result = generate_weather_slots(
            slot_count=slot_count,
            unique=unique,
            profile=profile,
            fixed_slots={},
        )
    except ValueError as exc:
        return jsonify({"error": "draw_failed", "detail": str(exc)}), 400

    return jsonify(
        {
            "ok": True,
            "slot_count": slot_count,
            "profile": profile,
            "unique": unique,
            "codes": result,
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
