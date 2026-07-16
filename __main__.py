"""Allow ``python __main__.py`` to use the installed CLI implementation."""

from social_pulse_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
