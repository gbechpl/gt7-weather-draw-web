from __future__ import annotations

try:
    import ujson as json
except ImportError:
    import json

try:
    import uos as os
except ImportError:
    import os


STATE_FILE = "discord_state.json"
LAST_SEEN_MESSAGE_IDS = {}


def load_seen_message_ids():
    global LAST_SEEN_MESSAGE_IDS

    try:
        with open(STATE_FILE, "r") as plik:
            dane = json.load(plik)
    except Exception:
        LAST_SEEN_MESSAGE_IDS = {}
        return

    kanaly = dane.get("channels", {}) if isinstance(dane, dict) else {}
    if not isinstance(kanaly, dict):
        LAST_SEEN_MESSAGE_IDS = {}
        return

    LAST_SEEN_MESSAGE_IDS = {
        str(kanal_id): str(message_id)
        for kanal_id, message_id in kanaly.items()
        if message_id
    }


def save_seen_message_id(channel_id, message_id):
    klucz = str(channel_id)
    wartosc = str(message_id)

    if LAST_SEEN_MESSAGE_IDS.get(klucz) == wartosc:
        return

    LAST_SEEN_MESSAGE_IDS[klucz] = wartosc
    _save_state()


def get_last_seen_message_id(channel_id):
    return LAST_SEEN_MESSAGE_IDS.get(str(channel_id))


def is_newer_message(message_id, last_seen_id):
    if not message_id:
        return False

    if not last_seen_id:
        return True

    try:
        return int(message_id) > int(last_seen_id)
    except Exception:
        return str(message_id) > str(last_seen_id)


def _save_state():
    dane = {"channels": LAST_SEEN_MESSAGE_IDS}
    tmp_file = STATE_FILE + ".tmp"

    try:
        with open(tmp_file, "w") as plik:
            json.dump(dane, plik)
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass
        os.rename(tmp_file, STATE_FILE)
    except Exception:
        try:
            os.remove(tmp_file)
        except Exception:
            pass
