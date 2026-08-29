"""
Baked-in app version.

Bump this manually before creating a new GitHub Release when
building a packaged .exe (PyInstaller) — the packaged app has
no .git directory to read a version from, so this constant is
the only source of truth for "what version is this build".

Source checkouts (running `python main.py` directly) don't use
this at all — they compare git commit hashes instead, see
core/version_check.py.
"""

__version__ = "1.0.2"
