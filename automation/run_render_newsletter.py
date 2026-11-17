"""Run the existing guarded sender on Render's allowlisted regional egress."""
import os
import signal
import sys
import urllib.error

from automation import build_weekly_newsletter, send_brevo_newsletter


def main():
    if os.environ.get("RENDER") != "true":
        raise ValueError("This entry point requires the Render runtime")
    if os.environ.get("BREVO_SEND_RUNTIME") != "render":
        raise ValueError("Render newsletter runtime not selected")
    # Bound compute time even if a dependency stalls. No background process survives.
    signal.alarm(240)
    try:
        build_weekly_newsletter.build()
        send_brevo_newsletter.main()
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, urllib.error.URLError) as exc:
        print("FAIL CLOSED:", str(exc), file=sys.stderr)
        sys.exit(1)
