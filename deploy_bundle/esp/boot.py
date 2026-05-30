try:
    import webrepl

    webrepl.start()
    print("WebREPL started")
except Exception as exc:
    print("WebREPL failed:", exc)
