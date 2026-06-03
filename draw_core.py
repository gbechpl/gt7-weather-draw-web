from __future__ import annotations

import random


SUNNY = [f"S{i:02d}" for i in range(1, 19)]
CLOUDY = [f"C{i:02d}" for i in range(1, 7)]
RAIN = [f"R{i:02d}" for i in range(1, 9)]
ALL_WEATHER = SUNNY + CLOUDY + RAIN

PROFILES = {
    "dry": {"sunny": 8.5, "cloudy": 1.5, "rain": 0.0},
    "equal": {"sunny": 1.0, "cloudy": 1.0, "rain": 1.0},
    "mixed": {"sunny": 3.0, "cloudy": 3.0, "rain": 2.0},
    "wet": {"sunny": 1.5, "cloudy": 3.0, "rain": 5.5},
}


def weighted_code(profile: str) -> str:
    weights = PROFILES[profile]
    bucket = random.choices(
        population=["sunny", "cloudy", "rain"],
        weights=[weights["sunny"], weights["cloudy"], weights["rain"]],
        k=1,
    )[0]

    if bucket == "sunny":
        return random.choice(SUNNY)
    if bucket == "cloudy":
        return random.choice(CLOUDY)
    return random.choice(RAIN)


def generate_weather_slots(
    slot_count: int,
    unique: bool,
    profile: str,
    fixed_slots: dict[int, str] | None = None,
    seed: str | int | None = None,
) -> list[str]:
    rng = random.Random(seed) if seed is not None else random
    if slot_count < 1:
        raise ValueError("slot_count must be >= 1")
    if profile not in PROFILES:
        raise ValueError("unknown profile")
    if unique and slot_count > len(ALL_WEATHER):
        raise ValueError("too many unique slots requested")

    fixed_slots = fixed_slots or {}
    seen: set[str] = set()
    slots: list[str | None] = [None] * slot_count

    for position, code in fixed_slots.items():
        if position < 1 or position > slot_count:
            raise ValueError(f"slot {position} out of range")
        if code not in ALL_WEATHER:
            raise ValueError(f"unknown code {code}")
        slots[position - 1] = code
        if unique:
            if code in seen:
                raise ValueError("duplicate fixed slot for unique draw")
            seen.add(code)

    missing_positions = [idx for idx, code in enumerate(slots) if code is None]

    if unique and profile == "equal":
        pool = [code for code in ALL_WEATHER if code not in seen]
        sampled = rng.sample(pool, k=len(missing_positions))
        for idx, code in zip(missing_positions, sampled):
            slots[idx] = code
        return [code for code in slots if code is not None]

    for idx in missing_positions:
        while True:
            code = weighted_code(profile) if seed is None else _weighted_code(profile, rng)
            if unique and code in seen:
                continue
            slots[idx] = code
            if unique:
                seen.add(code)
            break

    return [code for code in slots if code is not None]


def _weighted_code(profile: str, rng: random.Random) -> str:
    weights = PROFILES[profile]
    bucket = rng.choices(
        population=["sunny", "cloudy", "rain"],
        weights=[weights["sunny"], weights["cloudy"], weights["rain"]],
        k=1,
    )[0]

    if bucket == "sunny":
        return rng.choice(SUNNY)
    if bucket == "cloudy":
        return rng.choice(CLOUDY)
    return rng.choice(RAIN)
