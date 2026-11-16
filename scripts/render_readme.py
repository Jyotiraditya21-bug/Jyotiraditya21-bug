#!/usr/bin/env python3
"""Render the profile README and refresh its dynamic repository/activity blocks."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".github" / "profile.env"
TEMPLATE = ROOT / "README.template.md"
OUTPUT = ROOT / "README.md"


def read_username() -> str:
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        if line.startswith("GITHUB_USERNAME="):
            username = line.split("=", 1)[1].strip()
            if username:
                return username
    raise SystemExit("GITHUB_USERNAME is missing from .github/profile.env")


def github_json(path: str) -> list[dict]:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-readme-renderer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def latest_repos(username: str) -> str:
    repos = github_json(f"/users/{username}/repos?sort=updated&per_page=6&type=owner")
    rows = []
    for repo in repos:
        if repo.get("fork") or repo["name"].lower() == username.lower():
            continue
        language = repo.get("language") or "Mixed"
        rows.append(
            f"- [`{repo['name']}`]({repo['html_url']}) · {language} · "
            f"★ {repo['stargazers_count']}"
        )
        if len(rows) == 4:
            break
    return "\n".join(rows) or "- Repository feed is ready for its first public item."


def recent_activity(username: str) -> str:
    events = github_json(f"/users/{username}/events/public?per_page=30")
    labels = {
        "PushEvent": "Pushed to",
        "PullRequestEvent": "Updated a pull request in",
        "IssuesEvent": "Updated an issue in",
        "IssueCommentEvent": "Commented in",
        "CreateEvent": "Created a ref in",
        "ReleaseEvent": "Published a release in",
        "ForkEvent": "Forked",
        "WatchEvent": "Starred",
    }
    rows, seen = [], set()
    for event in events:
        repo = event.get("repo", {}).get("name", "")
        kind = event.get("type", "")
        key = (kind, repo)
        if not repo or key in seen or kind not in labels:
            continue
        seen.add(key)
        rows.append(f"- {labels[kind]} [`{repo}`](https://github.com/{repo})")
        if len(rows) == 4:
            break
    return "\n".join(rows) or "- Public activity feed is ready for its first event."


def main() -> None:
    username = read_username()
    template = TEMPLATE.read_text(encoding="utf-8")
    try:
        repos = latest_repos(username)
        activity = recent_activity(username)
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"GitHub refresh unavailable; preserving current dynamic blocks: {error}")
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else template
        repos = between(current, "LATEST_REPOS")
        activity = between(current, "RECENT_ACTIVITY")
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    rendered = (
        template.replace("__GITHUB_USERNAME__", username)
        .replace("__LATEST_REPOS__", repos)
        .replace("__RECENT_ACTIVITY__", activity)
        .replace("__LAST_UPDATED__", stamp)
    )
    OUTPUT.write_text(rendered, encoding="utf-8")


def between(text: str, name: str) -> str:
    start = f"<!-- {name}:START -->"
    end = f"<!-- {name}:END -->"
    if start in text and end in text:
        value = text.split(start, 1)[1].split(end, 1)[0].strip()
        if value and not value.startswith("__"):
            return value
    if name == "LATEST_REPOS":
        return "- The scheduled repository feed activates on the first workflow run."
    return "- The scheduled activity feed activates on the first workflow run."


if __name__ == "__main__":
    main()

