from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from draw_core import ALL_WEATHER, PROFILES, generate_weather_slots


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))


@app.get("/")
def index():
    return render_template(
        "index.html",
        profiles=sorted(PROFILES.keys()),
        weather_count=len(ALL_WEATHER),
    )


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/draw")
def api_draw():
    payload = request.get_json(silent=True) or {}

    try:
        slot_count = max(1, min(9, int(payload.get("slot_count", 9))))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_slot_count"}), 400

    profile = str(payload.get("profile", "mixed")).strip().lower() or "mixed"
    if profile not in PROFILES:
        return jsonify({"error": "invalid_profile", "profiles": sorted(PROFILES.keys())}), 400

    unique = bool(payload.get("unique", False))

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
