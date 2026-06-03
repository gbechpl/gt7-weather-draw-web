def log(msg):
    print(msg)
    try:
        with open("boot.log", "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


log("START boot.py")

# Keep boot minimal; main.py should still autostart.
