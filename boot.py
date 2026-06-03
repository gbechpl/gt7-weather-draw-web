print("START boot.py")
try:
    import webrepl

    webrepl.start()
except Exception:
    # Keep boot minimal; main.py should still autostart.
    pass
