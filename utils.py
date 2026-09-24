DEBUG = False


def debug_log(message: str) -> None:
    """Print a message only when the debug flag is on."""
    if DEBUG:
        print("[DEBUG] " + message)
