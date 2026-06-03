import machine
import time


def _in_safe_mode():
    try:
        # Many ESP32 boards expose a BOOT (GPIO0) button — hold it low during reset
        # to prevent auto-start. If pin reads low, we enter safe mode (stay in REPL).
        pin = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)
        return pin.value() == 0
    except Exception:
        return False


print("boot.py: checking BOOT pin for safe-mode (hold BOOT/GPIO0 while resetting)")
time.sleep(0.1)

if _in_safe_mode():
    print("boot.py: BOOT pin held low — entering safe mode. REPL available.")
    # Spin and let user use REPL; do not import main.
    while True:
        time.sleep(1)

# Not in safe mode — continue booting and import main (if present)
print("boot.py: continuing normal boot...")
try:
    import main
except Exception as e:
    print("boot.py: error importing main:", e)


def log(msg):
    print(msg)
    try:
        with open("boot.log", "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


log("START boot.py")

# Keep boot minimal; main.py should still autostart.
