"""
Update check for a packaged build (PyInstaller .exe).

A packaged app has no .git directory and no git binary
guaranteed on the target machine, so it can't use the
git-based check in core/version_check.py. Instead it asks the
GitHub Releases API for the latest published release and
compares its tag against the version baked in at build time
(core/app_version.__version__).

Never raises — any failure (offline, API error, bad response)
is reported as status "unknown" so it can never block or crash
app startup.
"""

import json
import urllib.request
import urllib.error


def _parse_version(text):
    """
    "v1.2.0" / "1.2.0" -> (1, 2, 0). Non-numeric parts are
    dropped rather than raising, so odd tags like "1.2.0-beta"
    still compare on their numeric prefix.
    """

    text = text.strip().lstrip("vV")

    parts = []

    for chunk in text.split("."):

        digits = ""

        for ch in chunk:

            if ch.isdigit():

                digits += ch

            else:

                break

        parts.append(int(digits) if digits else 0)

    return tuple(parts)


def check_github_release(
    owner,
    repo,
    current_version,
    timeout=5.0,
):
    """
    Returns a dict:

        {
            "status": "up_to_date" | "outdated" | "unknown",
            "local": "<current version>",
            "remote": "<latest release tag>" or None,
            "url": "<release page URL>" or None,
        }

    Never raises.
    """

    result = {
        "status": "unknown",
        "local": current_version,
        "remote": None,
        "url": None,
    }

    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}"
        "/releases/latest"
    )

    request = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{repo}-update-check",
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            payload = json.loads(
                response.read().decode("utf-8")
            )

    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        Exception,
    ):

        return result

    tag = payload.get("tag_name")

    if not tag:

        return result

    result["remote"] = tag

    result["url"] = payload.get("html_url")

    try:

        local_v = _parse_version(current_version)

        remote_v = _parse_version(tag)

    except Exception:

        return result

    result["status"] = (
        "outdated"
        if remote_v > local_v
        else "up_to_date"
    )

    return result
