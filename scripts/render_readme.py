#!/usr/bin/env python3
"""Render the profile README and refresh its dynamic repository/activity blocks."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
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


def github_json(path: str) -> object:
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


def write_metrics(username: str) -> None:
    profile = github_json(f"/users/{username}")
    repos = github_json(f"/users/{username}/repos?sort=updated&per_page=100&type=owner")
    owned = [repo for repo in repos if not repo.get("fork")]
    stars = sum(repo.get("stargazers_count", 0) for repo in owned)
    forks = sum(repo.get("forks_count", 0) for repo in owned)
    languages = Counter(repo.get("language") for repo in owned if repo.get("language"))
    top_languages = languages.most_common(5)
    language_total = sum(count for _, count in top_languages) or 1
    colors = ["#67E8F9", "#60A5FA", "#A5B4FC", "#38BDF8", "#64748B"]
    x = 64.0
    segments = []
    labels = []
    for index, ((language, count), color) in enumerate(zip(top_languages, colors)):
        width = 872 * count / language_total
        segments.append(
            f'<rect x="{x:.1f}" y="202" width="{width:.1f}" height="8" fill="{color}"/>'
        )
        label_x = 64 + index * 174
        labels.append(
            f'<circle cx="{label_x}" cy="242" r="4" fill="{color}"/>'
            f'<text x="{label_x + 12}" y="247" class="label">{escape(language)}</text>'
        )
        x += width
    svg = f'''<svg width="1000" height="280" viewBox="0 0 1000 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub repository metrics">
  <style>
    .kicker {{ font: 500 12px ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: 2px; fill: #64748B; }}
    .value {{ font: 700 34px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #F8FAFC; }}
    .caption {{ font: 500 12px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #94A3B8; }}
    .label {{ font: 500 12px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #CBD5E1; }}
  </style>
  <rect x="1" y="1" width="998" height="278" rx="18" fill="#0B0F14" stroke="#1E293B" stroke-width="2"/>
  <text x="64" y="48" class="kicker">REPOSITORY SIGNAL</text>
  <path d="M64 66H936" stroke="#1E293B"/>
  <g text-anchor="middle">
    <text x="160" y="126" class="value">{profile.get('public_repos', len(owned))}</text><text x="160" y="151" class="caption">PUBLIC REPOS</text>
    <text x="385" y="126" class="value">{stars}</text><text x="385" y="151" class="caption">STARS</text>
    <text x="615" y="126" class="value">{forks}</text><text x="615" y="151" class="caption">FORKS</text>
    <text x="840" y="126" class="value">{profile.get('followers', 0)}</text><text x="840" y="151" class="caption">FOLLOWERS</text>
  </g>
  <path d="M272 92V151M500 92V151M728 92V151" stroke="#1E293B"/>
  <text x="64" y="187" class="kicker">PRIMARY LANGUAGES BY REPOSITORY</text>
  <clipPath id="bar"><rect x="64" y="202" width="872" height="8" rx="4"/></clipPath>
  <g clip-path="url(#bar)">{''.join(segments)}</g>
  {''.join(labels)}
</svg>'''
    metrics_path = ROOT / "assets" / "metrics.svg"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(svg, encoding="utf-8")


def main() -> None:
    username = read_username()
    template = TEMPLATE.read_text(encoding="utf-8")
    try:
        repos = latest_repos(username)
        activity = recent_activity(username)
        write_metrics(username)
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

