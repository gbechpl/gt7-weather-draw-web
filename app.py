from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from draw_core import ALL_WEATHER, PROFILES, generate_weather_slots
from png_render import render_weather_draw_png


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


def parse_optional_bool(value, default: bool, error_code: str) -> bool:
    if value is None or value == "":
        return default
    try:
        return parse_unique_flag(value)
    except ValueError as exc:
        raise ValueError(error_code) from exc


def parse_int_param(value, default: int, minimum: int, maximum: int, error_code: str):
    if value is None or value == "":
        return default
    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(error_code) from exc
    if parsed_value < minimum or parsed_value > maximum:
        raise ValueError(error_code)
    return parsed_value


def collect_draw_payload() -> dict:
    payload: dict = {}

    json_payload = request.get_json(silent=True)
    if isinstance(json_payload, dict):
        payload.update(json_payload)

    if request.form:
        payload.update(request.form.to_dict(flat=True))

    if request.args:
        payload.update(request.args.to_dict(flat=True))

    return payload


def resolve_draw_context() -> tuple[dict | None, tuple[Response, int] | None]:
    payload = collect_draw_payload()

    try:
        slot_count = parse_int_param(payload.get("slot_count"), default=9, minimum=3, maximum=9, error_code="invalid_slot_count")
    except ValueError:
        return None, (jsonify({"error": "invalid_slot_count", "min": 3, "max": 9}), 400)

    profile = str(payload.get("profile", "mixed")).strip().lower() or "mixed"
    if profile not in PROFILES:
        return None, (jsonify({"error": "invalid_profile", "profiles": sorted(PROFILES.keys())}), 400)

    try:
        unique = parse_unique_flag(payload.get("unique", False))
    except ValueError:
        return None, (jsonify({"error": "invalid_unique"}), 400)

    try:
        animate = parse_optional_bool(payload.get("animate"), default=True, error_code="invalid_animate")
    except ValueError:
        return None, (jsonify({"error": "invalid_animate"}), 400)

    return {
        "payload": payload,
        "slot_count": slot_count,
        "profile": profile,
        "unique": unique,
        "animate": animate,
    }, None


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


@app.route("/api/draw", methods=["GET", "POST"])
@app.route("/api/draw/start", methods=["GET", "POST"])
def api_draw():
    context, error_response = resolve_draw_context()
    if error_response is not None:
        return error_response

    slot_count = context["slot_count"]
    profile = context["profile"]
    unique = context["unique"]
    animate = context["animate"]

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
            "endpoint": request.path,
            "source": "query" if request.args else "json_or_form",
            "animate": animate,
            "slot_count": slot_count,
            "profile": profile,
            "unique": unique,
            "codes": result,
        }
    )


@app.route("/api/draw/image", methods=["GET", "POST"])
@app.route("/api/draw/png", methods=["GET", "POST"])
def api_draw_image():
    context, error_response = resolve_draw_context()
    if error_response is not None:
        return error_response

    try:
        result = generate_weather_slots(
            slot_count=context["slot_count"],
            unique=context["unique"],
            profile=context["profile"],
            fixed_slots={},
        )
    except ValueError as exc:
        return jsonify({"error": "draw_failed", "detail": str(exc)}), 400

    png_bytes = render_weather_draw_png(
        codes=result,
        profile=context["profile"],
        unique=context["unique"],
        sprite_path=BASE_DIR / "static" / "icons" / "sprite_small.png",
    )
    response = Response(png_bytes, mimetype="image/png")
    response.headers["Content-Disposition"] = (
        f'inline; filename="gt7-draw-{context["profile"]}-{context["slot_count"]}.png"'
    )
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
