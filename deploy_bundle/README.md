# GT7 deployment bundle

To jest gotowy zestaw plików do przeniesienia na dwa cele:

## `esp/`

Pliki dla ESP32 / MicroPython:

- `boot.py`
- `main.py`
- `config.example.py`

Uwagi:

- `config.example.py` to bezpieczny szablon do wrzucenia na GitHuba.
- Prawdziwy `config.py` zawiera Wi-Fi, token Discorda i webhooki, więc trzymaj go lokalnie na ESP.
- `urequests.py` nie jest częścią repo. Jeśli firmware ESP go nie ma, trzeba go dograć osobno.

## `render/`

Pliki dla Render Web Service:

- `app.py`
- `draw_core.py`
- `png_render.py`
- `requirements.txt`
- `Procfile`
- `render.yaml`
- `.python-version`
- `templates/`
- `static/`

To jest minimalny zestaw potrzebny do uruchomienia web service na Renderze.

## Keepalive

Poza Renderem możesz użyć skryptu `keepalive_ping.py` z głównego katalogu repo, żeby pingować:

- `https://gt7-weather-draw-web-1wmp.onrender.com/keepalive`
- albo `.../ping`

Najprościej ustawić go w Harmonogramie zadań co 10 minut albo w cron.

## Keepalive w bocie Discord

Jeśli uruchamiasz `bot_vs.py` stale, możesz ustawić:

- `KEEPALIVE_URL=https://twoj-serwis.onrender.com/keepalive`
- `KEEPALIVE_ENABLED=1`
- `KEEPALIVE_INTERVAL_SECONDS=600`

Wtedy bot będzie pingował Render w tle co 10 minut.

## Keepalive na ESP

W `esp/main.py` bot na ESP też pinguję Render co `KEEPALIVE_INTERVAL_MS`.

W `esp/config.py` masz:

- `KEEPALIVE_URL`
- `KEEPALIVE_INTERVAL_MS`

Domyślnie ping idzie na `/keepalive` co 10 minut.
