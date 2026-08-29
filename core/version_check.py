"""
Startup version check.

Compares the local git HEAD commit against the latest commit
on the remote branch, so the app can notify the user when
they're running an outdated checkout.

Pure git-based (no VERSION file to keep in sync manually, no
external service) — works as long as the working directory is
a git checkout with a reachable `origin` remote. Any failure
(not a git repo, no network, git not installed, ...) is
swallowed and reported as "unknown", never raised — this check
must never block or crash app startup.
"""

import subprocess


def _run_git(args, cwd, timeout):

    try:

        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    except Exception:

        return None

    if result.returncode != 0:

        return None

    return result.stdout.strip()


def check_for_update(
    repo_dir,
    branch=None,
    remote="origin",
    timeout=3.0,
):
    """
    Returns a dict:

        {
            "status": "up_to_date" | "outdated" | "unknown",
            "local": "<short hash>" or None,
            "remote": "<short hash>" or None,
            "branch": "<branch name>" or None,
        }

    Never raises.
    """

    result = {
        "status": "unknown",
        "local": None,
        "remote": None,
        "branch": branch,
    }

    if branch is None:

        branch = _run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            repo_dir,
            timeout,
        )

        if not branch or branch == "HEAD":

            return result

        result["branch"] = branch

    local_hash = _run_git(
        ["rev-parse", "HEAD"],
        repo_dir,
        timeout,
    )

    if not local_hash:

        return result

    result["local"] = local_hash[:8]

    remote_output = _run_git(
        [
            "ls-remote",
            remote,
            f"refs/heads/{branch}",
        ],
        repo_dir,
        timeout,
    )

    if not remote_output:

        return result

    remote_hash = remote_output.split()[0]

    result["remote"] = remote_hash[:8]

    result["status"] = (
        "up_to_date"
        if remote_hash == local_hash
        else "outdated"
    )

    return result
