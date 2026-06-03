from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from draw_core import ALL_WEATHER, PROFILES, generate_weather_slots
from png_render import render_weather_draw_png


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
CACHE_DIR = BASE_DIR / "cache" / "weather_draws"
CACHE_LOCKS: dict[str, threading.Lock] = {}
CACHE_LOCKS_GUARD = threading.Lock()
CACHE_REGEN_PENDING: set[str] = set()
CACHE_REGEN_GUARD = threading.Lock()
CACHE_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gt7-cache")
CACHE_VARIANTS = 2
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


def cache_key(profile: str, slot_count: int, unique: bool) -> str:
    return f"{profile}-{slot_count}-u{int(unique)}"


def cache_variant_key(profile: str, slot_count: int, unique: bool, variant: int) -> str:
    return f"{cache_key(profile, slot_count, unique)}-v{variant}"


def cache_path(profile: str, slot_count: int, unique: bool, variant: int = 0) -> Path:
    return CACHE_DIR / f"{cache_variant_key(profile, slot_count, unique, variant)}.png"


def get_cache_lock(key: str) -> threading.Lock:
    with CACHE_LOCKS_GUARD:
        lock = CACHE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            CACHE_LOCKS[key] = lock
        return lock


def write_png_atomically(path: Path, png_bytes: bytes) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(png_bytes)
    os.replace(tmp_path, path)


def cache_snapshot() -> dict:
    items: list[dict] = []
    if CACHE_DIR.exists():
        for file_path in sorted(CACHE_DIR.glob("*.png")):
            stat = file_path.stat()
            items.append(
                {
                    "file": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    return {
        "cache_dir": str(CACHE_DIR),
        "cached_files": items,
        "cached_count": len(items),
        "pending_regeneration": sorted(CACHE_REGEN_PENDING),
    }


def render_draw_png(slot_count: int, profile: str, unique: bool, seed: str | None = None) -> bytes:
    result = generate_weather_slots(
        slot_count=slot_count,
        unique=unique,
        profile=profile,
        fixed_slots={},
        seed=seed,
    )
    return render_weather_draw_png(
        codes=result,
        profile=profile,
        unique=unique,
        sprite_path=BASE_DIR / "static" / "icons" / "sprite_small.png",
    )


def regenerate_cache_entry(profile: str, slot_count: int, unique: bool, variant: int) -> None:
    key = cache_variant_key(profile, slot_count, unique, variant)
    path = cache_path(profile, slot_count, unique, variant)

    try:
        app.logger.info("Regenerating cache entry %s", key)
        png_bytes = render_draw_png(slot_count=slot_count, profile=profile, unique=unique)
        write_png_atomically(path, png_bytes)
        app.logger.info("Cache entry ready %s (%d bytes)", key, len(png_bytes))
    except Exception:
        app.logger.exception("Failed to regenerate cache entry %s", key)
    finally:
        with CACHE_REGEN_GUARD:
            CACHE_REGEN_PENDING.discard(key)


def schedule_cache_regeneration(profile: str, slot_count: int, unique: bool, variant: int) -> None:
    key = cache_variant_key(profile, slot_count, unique, variant)
    with CACHE_REGEN_GUARD:
        if key in CACHE_REGEN_PENDING:
            return
        CACHE_REGEN_PENDING.add(key)
    CACHE_EXECUTOR.submit(regenerate_cache_entry, profile, slot_count, unique, variant)


def get_cached_png(profile: str, slot_count: int, unique: bool) -> bytes:
    served_variant: int | None = None
    for variant in range(CACHE_VARIANTS):
        key = cache_variant_key(profile, slot_count, unique, variant)
        path = cache_path(profile, slot_count, unique, variant)
        if path.exists():
            app.logger.info("Cache hit %s", key)
            png_bytes = path.read_bytes()
            served_variant = variant
            break

    if served_variant is None:
        variant = 0
        key = cache_variant_key(profile, slot_count, unique, variant)
        path = cache_path(profile, slot_count, unique, variant)
        lock = get_cache_lock(key)

        with lock:
            if path.exists():
                app.logger.info("Cache hit after lock %s", key)
                png_bytes = path.read_bytes()
            else:
                app.logger.info("Cache miss %s", key)
                png_bytes = render_draw_png(slot_count=slot_count, profile=profile, unique=unique)
                write_png_atomically(path, png_bytes)
        served_variant = variant

    for variant in range(CACHE_VARIANTS):
        if variant == served_variant:
            schedule_cache_regeneration(profile, slot_count, unique, variant)
            continue
        other_path = cache_path(profile, slot_count, unique, variant)
        if not other_path.exists():
            schedule_cache_regeneration(profile, slot_count, unique, variant)

    return png_bytes


def prewarm_cache() -> None:
    for profile in sorted(PROFILES.keys()):
        for slot_count in range(3, 10):
            for variant in range(CACHE_VARIANTS):
                schedule_cache_regeneration(profile, slot_count, unique=False, variant=variant)


@app.get("/_cache_status")
def cache_status():
    return jsonify(cache_snapshot())


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

    seed_value = payload.get("seed")
    seed = None if seed_value is None or seed_value == "" else str(seed_value).strip()

    return {
        "payload": payload,
        "slot_count": slot_count,
        "profile": profile,
        "unique": unique,
        "animate": animate,
        "seed": seed,
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


@app.get("/keepalive")
@app.get("/ping")
def keepalive():
    response = jsonify({"ok": True})
    response.headers["Cache-Control"] = "no-store"
    return response


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
        if context["unique"] or context["seed"] is not None:
            png_bytes = render_draw_png(
                slot_count=context["slot_count"],
                profile=context["profile"],
                unique=context["unique"],
                seed=context["seed"],
            )
        else:
            png_bytes = get_cached_png(
                profile=context["profile"],
                slot_count=context["slot_count"],
                unique=context["unique"],
            )
    except ValueError as exc:
        return jsonify({"error": "draw_failed", "detail": str(exc)}), 400

    response = Response(png_bytes, mimetype="image/png")
    response.headers["Content-Disposition"] = (
        f'inline; filename="gt7-draw-{context["profile"]}-{context["slot_count"]}.png"'
    )
    response.headers["Cache-Control"] = "no-store"
    return response


prewarm_cache()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
