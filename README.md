# GT7 Weather Draw Web

Samodzielny projekt webowy z maszyną losującą pogodę dla Gran Turismo 7.

## Co zawiera

- backend Flask z endpointem `POST /api/draw`
- frontend z animacją slotów w przeglądarce
- gotowy asset `sprite_small.png`
- pliki pod wdrożenie na zewnętrzny hosting

## Struktura

- `app.py` - aplikacja Flask
- `draw_core.py` - logika losowania
- `templates/index.html` - widok strony
- `static/css/styles.css` - stylowanie
- `static/js/app.js` - animacja i komunikacja z API
- `static/icons/sprite_small.png` - sprite warunków pogodowych

## Uruchomienie lokalne

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Strona będzie dostępna pod:

```text
http://127.0.0.1:8000
```

## ESP32-S3 i WebREPL

Plik `boot.py` uruchamia WebREPL automatycznie po starcie płytki.

Jeśli WebREPL nie ma jeszcze ustawionego hasła, uruchom na ESP32 jednorazowo `webrepl_setup` i ustaw hasło przez konsolę MicroPythona.

## Lokalny bot do testów

Plik `bot_vs.py` uruchamia bota Discord lokalnie z VS Code i pobiera gotowy obraz z Rendera.

Uruchom:

```bash
python bot_vs.py
```

Do testu lokalnego:

```bash
python bot_vs.py --local
```

Wymaga to:
- `DISCORD_TOKEN`
- `WEB_SERVICE_URL`
- włączenia `Message Content Intent` w Discord Developer Portal, jeśli używasz komendy tekstowej `!pogoda`

Jeśli chcesz odpalać stronę lokalnie, ustaw:

```bash
set GT7_USE_LOCAL_WEB_SERVICE=true
python app.py
python bot_vs.py
```

Wtedy bot będzie brał PNG z `http://127.0.0.1:8000` zamiast z Rendera.

Przydatna komenda diagnostyczna:

```text
!status
```

Ta komenda pobiera PNG z web service i odsyła go na kanał, więc szybko pokaże, czy połączenie działa.

Możesz też uruchomić całość jednym kliknięciem przez `run_local.bat`.

## Deployment na Render

Projekt jest przygotowany pod Render Web Service.

### Pliki pod Render

- `render.yaml` - gotowa konfiguracja usługi
- `.python-version` - przypięta wersja Pythona
- `requirements.txt` - zależności
- `Procfile` - alternatywna komenda startowa

### Wariant 1: z `render.yaml`

1. Wrzuć katalog `gt7_weather_draw_web` do osobnego repozytorium.
2. Na Render wybierz `New +` -> `Blueprint`.
3. Wskaż repozytorium z tym projektem.
4. Render odczyta `render.yaml` i utworzy usługę automatycznie.

### Wariant 2: ręcznie jako Web Service

Ustaw:

```text
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --bind 0.0.0.0:$PORT
```

### Zmienne środowiskowe

- `PORT` - ustawiany automatycznie przez Render

### Po wdrożeniu

Render nada publiczny adres w domenie `onrender.com`.

Endpoint zdrowia:

```text
/health
```

## Budzenie Rendera co 10 minut

Free web service na Renderze usypia po 15 minutach bez ruchu. Żeby go utrzymać aktywnego, ustaw zewnętrzny monitor, który będzie pingował:

```text
/keepalive
```

albo:

```text
/ping
```

Interwał 10 minut jest bezpieczny, bo jest krótszy niż limit bezczynności.

### Lokalny pinger

W repo jest prosty skrypt:

```text
keepalive_ping.py
```

Możesz go uruchamiać ręcznie albo przez Harmonogram zadań / cron:

```bash
python keepalive_ping.py
```

Na Windows najprościej ustawić zadanie cykliczne co 10 minut. Na Linuxie / serwerze:

```cron
*/10 * * * * /usr/bin/python3 /sciezka/do/gt7_weather_draw_web/keepalive_ping.py
```

Jeśli Render ma inny adres, podaj go parametrem:

```bash
python keepalive_ping.py --url https://twoj-serwis.onrender.com/keepalive
```

### Keepalive w bocie Discord

Jeśli bot działa cały czas, może sam pingować Rendera w tle. Ustaw:

- `KEEPALIVE_URL=https://twoj-serwis.onrender.com/keepalive`
- `KEEPALIVE_ENABLED=1`
- opcjonalnie `KEEPALIVE_INTERVAL_SECONDS=600`

Jeśli chcesz wyłączyć ping, ustaw:

```text
KEEPALIVE_ENABLED=0
```

## API

### `POST /api/draw`

Body:

```json
{
  "slot_count": 9,
  "profile": "mixed",
  "unique": false
}
```

Odpowiedź:

```json
{
  "ok": true,
  "slot_count": 9,
  "profile": "mixed",
  "unique": false,
  "codes": ["S03", "C01", "R07"]
}
```

### `GET /api/draw` albo `POST /api/draw/start`

Endpoint przyjmuje też dane z query string, formularza lub JSON, więc jest wygodny dla bota Discorda.

Przykład z query string:

```text
/api/draw/start?slot_count=6&profile=wet&unique=true
```

Przykład z JSON:

```json
{
  "slot_count": 6,
  "profile": "wet",
  "unique": true
}
```

W odpowiedzi dostaniesz ten sam format z polem `codes`, więc bot może od razu wysłać wynik na kanał albo dalej go przetworzyć.

### `GET /api/draw/image` albo `POST /api/draw/png`

To samo losowanie, ale wynik wraca jako plik `PNG` z ikonami i slotami pogodowymi.

Przykład:

```text
/api/draw/image?slot_count=6&profile=wet&unique=true
```

Ten wariant jest wygodny dla bota Discorda, bo można go pobrać i wysłać jako załącznik obrazu bez żadnego dodatkowego renderowania po stronie klienta.
