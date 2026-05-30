import gc
import machine
import network
import time
import urequests

import config


WIFI_SSID = config.WIFI_SSID
WIFI_PASS = config.WIFI_PASS
DISCORD_TOKEN = config.DISCORD_TOKEN
WEB_SERVICE_URL = config.WEB_SERVICE_URL.rstrip("/")
KEEPALIVE_URL = getattr(config, "KEEPALIVE_URL", WEB_SERVICE_URL.rstrip("/") + "/keepalive")
KEEPALIVE_INTERVAL_MS = int(getattr(config, "KEEPALIVE_INTERVAL_MS", 600000))

KANALE = [
    # (config.CH1_ID, config.CH1_WEBHOOK),
    (config.CH2_ID, config.CH2_WEBHOOK),
]

PROFILE_MAP = {
    "d": "dry",
    "b": "equal",
    "m": "mixed",
    "w": "wet",
}

PROFILE_LABELS = {
    "dry": "D (DRY)",
    "equal": "B (BALANCED)",
    "mixed": "M (MIXED)",
    "wet": "W (WET)",
}


def polacz_wifi():
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True

    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)

    timeout = 0
    while not wlan.isconnected():
        time.sleep(1)
        timeout += 1
        if timeout > 10:
            return False

    return True


def wyslij_pomoc(webhook_url):
    pelny_tekst = (
        "### GT7 WEATHER GENERATOR - HELP\n"
        "Wpisz: **!pogoda [preset][sloty]**\n\n"
        "**Dostepne presety:**\n"
        "**d** - DRY\n"
        "**b** - BALANCED\n"
        "**m** - MIXED\n"
        "**w** - WET\n\n"
        "**Liczba slotow:** od **3** do **9**\n\n"
        "**Przyklad:** `!pogoda m6`\n"
        "> -# Created by Gbech for GTSC"
    )

    payload = {"content": pelny_tekst}
    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        response = urequests.post(webhook_url, json=payload, headers=headers)
        response.close()
        print("-> Instrukcja pomocy wyslana na Discorda!")
    except Exception as exc:
        print("Blad wysylania pomocy:", exc)


def parse_command_text(text):
    czysty_tekst = text.strip().lower()
    if not czysty_tekst.startswith("!pogoda"):
        return None

    parts = czysty_tekst.split(None, 1)
    if len(parts) < 2:
        return None

    kod = parts[1].strip()
    if len(kod) < 2:
        return None

    profil = kod[0]
    if profil not in PROFILE_MAP:
        return None

    cyfry = []
    for znak in kod[1:]:
        if znak.isdigit():
            cyfry.append(znak)
        else:
            break

    if not cyfry:
        return None

    try:
        sloty = int("".join(cyfry))
    except ValueError:
        return None

    if sloty < 3 or sloty > 9:
        return None

    return profil, sloty


def build_service_url(profile_code, slot_count):
    profile = PROFILE_MAP.get(profile_code, "mixed")
    return "{}/api/draw/image?slot_count={}&profile={}&unique=false&animate=false".format(
        WEB_SERVICE_URL, slot_count, profile
    )


def wyslij_wynik_jako_obraz(webhook_url, profil_code, slot_count, image_url):
    profil = PROFILE_MAP.get(profil_code, "mixed")
    tytul = "GT7 WEATHER GENERATOR"
    opis = "Preset {} | Slots: {}".format(PROFILE_LABELS.get(profil, profil), slot_count)

    payload = {
        "content": "",
        "embeds": [
            {
                "title": tytul,
                "description": opis,
                "image": {"url": image_url},
            }
        ],
    }

    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        response = urequests.post(webhook_url, json=payload, headers=headers)
        response.close()
        print("-> Obrazek wyslany pomyslnie!")
    except Exception as exc:
        print("Blad wysylania obrazu przez Webhook:", exc)


def przetworz_komende(tresc, webhook_url):
    parsed = parse_command_text(tresc)
    if parsed is None:
        wyslij_blad_formatu(webhook_url)
        return

    profil_code, slot_count = parsed
    image_url = build_service_url(profil_code, slot_count)
    print("-> Komenda wykryta:", tresc)
    print("-> Pobieranie obrazu:", image_url)
    wyslij_wynik_jako_obraz(webhook_url, profil_code, slot_count, image_url)


def wyslij_blad_formatu(webhook_url):
    payload = {
        "content": (
            "Nie rozpoznalem komendy. Uzyj np. `!pogoda w5` albo `!pogoda m6`."
        )
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        response = urequests.post(webhook_url, json=payload, headers=headers)
        response.close()
    except Exception as exc:
        print("Blad wysylania komunikatu o formacie:", exc)


def ping_keepalive():
    if not KEEPALIVE_URL:
        return

    res = None
    try:
        print("Ping keepalive:", KEEPALIVE_URL)
        res = urequests.get(KEEPALIVE_URL, timeout=10)
        print("Keepalive status:", res.status_code)
    except Exception as exc:
        print("Blad keepalive:", exc)
    finally:
        if res is not None:
            res.close()


if polacz_wifi():
    try:
        machine.Pin(38, machine.Pin.OUT).value(1)
    except Exception:
        pass

    print("GT7 bot wystartowal i czuwa 24/7...")
    wdt = machine.WDT(timeout=30000)
    headers_pobierania = {"Authorization": "Bot {}".format(DISCORD_TOKEN)}
    wykonane_komendy_ids = []
    czas_startu = time.ticks_ms()
    czas_ostatniego_keepalive = czas_startu

    while True:
        try:
            wdt.feed()

            if time.ticks_diff(time.ticks_ms(), czas_startu) > 86400000:
                print("Dobowy restart systemu dla zachowania stabilnosci RAM...")
                time.sleep(1)
                machine.reset()

            gc.collect()

            if KEEPALIVE_URL and time.ticks_diff(time.ticks_ms(), czas_ostatniego_keepalive) >= KEEPALIVE_INTERVAL_MS:
                ping_keepalive()
                czas_ostatniego_keepalive = time.ticks_ms()

            if not network.WLAN(network.STA_IF).isconnected():
                print("Utracono Wi-Fi! Proba ponownego polaczenia...")
                if not polacz_wifi():
                    print("Nie udalo sie polaczyc z Wi-Fi. Ponawiam...")
                    time.sleep(3)
                    continue

            for discord_channel_id, discord_webhook_url in KANALE:
                wdt.feed()

                url_pobierania = "https://discord.com/api/v10/channels/{}/messages?limit=5".format(
                    discord_channel_id
                )

                res = None
                try:
                    res = urequests.get(url_pobierania, headers=headers_pobierania, timeout=10)
                    print("Kanal: {} | Status: {}".format(discord_channel_id, res.status_code))

                    if res.status_code == 200:
                        wiadomosci = res.json()
                        for msg in reversed(wiadomosci):
                            tresc = msg.get("content", "").strip()
                            msg_id = msg.get("id")
                            autor_bot = msg.get("author", {}).get("bot", False)

                            if autor_bot or (msg_id in wykonane_komendy_ids):
                                continue

                            tresc_lc = tresc.lower()

                            if tresc_lc in ("!pogoda ?", "!pogoda help"):
                                wykonane_komendy_ids.append(msg_id)
                                print("Wykryto prośbę o pomoc na kanale {}".format(discord_channel_id))
                                wyslij_pomoc(discord_webhook_url)

                            elif tresc_lc.startswith("!pogoda "):
                                wykonane_komendy_ids.append(msg_id)
                                przetworz_komende(tresc, discord_webhook_url)

                except Exception as inner_exc:
                    print("Blad podczas obslugi kanalu {}: {}".format(discord_channel_id, inner_exc))
                finally:
                    if res is not None:
                        res.close()

                time.sleep(1)

            while len(wykonane_komendy_ids) > 50:
                wykonane_komendy_ids.pop(0)

        except Exception as exc:
            print("Glowny blad petli, ponawiam...", exc)

        time.sleep(3)
