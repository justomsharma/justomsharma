"""Live GitHub numbers for the card. Stdlib only, so the Action needs no installs.

Falls back to the last good snapshot in cache/stats.json when the API is
unreachable, so a flaky run never publishes a broken or zeroed card.
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

API = "https://api.github.com"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes { nameWithOwner stargazerCount }
    }
    repositoriesContributedTo(
      first: 100, includeUserRepositories: false,
      contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]
    ) {
      totalCount
      nodes { nameWithOwner }
    }
    contributionsCollection { contributionCalendar { totalContributions } }
  }
}
"""


@dataclass
class Stats:
    repos: int
    contributed: int
    stars: int
    followers: int
    commits: int
    contributions_1y: int
    additions: int
    deletions: int
    # repo -> [commits, additions, deletions]; lets one slow repo fall back
    # to its last known totals instead of discarding the whole live run.
    per_repo: dict[str, list[int]] = field(default_factory=dict, compare=False)

    @property
    def loc(self) -> int:
        return max(0, self.additions - self.deletions)


class StatsError(RuntimeError):
    pass


class StillComputing(StatsError):
    pass


Fetch = Callable[[str, str, bytes | None], tuple[int, object]]


def _http(token: str) -> Fetch:
    def fetch(method: str, url: str, body: bytes | None) -> tuple[int, object]:
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "justomsharma-profile-card")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            return e.code, None

    return fetch


def _contributor_totals(
    fetch: Fetch, repo: str, login: str, retries: int, wait: float
) -> tuple[int, int, int]:
    """(commits, additions, deletions) by `login` in `repo`.

    GitHub computes these lazily and answers 202 until the numbers are ready.
    """
    for _ in range(retries):
        status, data = fetch("GET", f"{API}/repos/{repo}/stats/contributors", None)
        if status == 200 and isinstance(data, list):
            for c in data:
                if (c.get("author") or {}).get("login", "").lower() == login.lower():
                    weeks = c.get("weeks", [])
                    return (
                        c.get("total", 0),
                        sum(w.get("a", 0) for w in weeks),
                        sum(w.get("d", 0) for w in weeks),
                    )
            return 0, 0, 0
        if status == 204:  # empty repository
            return 0, 0, 0
        if status != 202:
            raise StatsError(f"stats/contributors {repo}: HTTP {status}")
        time.sleep(wait)
    raise StillComputing(f"stats/contributors {repo}: still computing after {retries} tries")


def fetch_stats(
    login: str,
    fetch: Fetch,
    retries: int = 10,
    wait: float = 3.0,
    previous: dict[str, list[int]] | None = None,
) -> Stats:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    status, data = fetch("POST", f"{API}/graphql", body)
    if status != 200 or not isinstance(data, dict) or data.get("errors") or not (data.get("data") or {}).get("user"):
        raise StatsError(f"graphql: HTTP {status} {data and data.get('errors')}")
    user = data["data"]["user"]

    owned = [r["nameWithOwner"] for r in user["repositories"]["nodes"]]
    contributed = [r["nameWithOwner"] for r in user["repositoriesContributedTo"]["nodes"]]
    repos = owned + contributed
    # Ask once for every repo first so GitHub computes them in parallel.
    for repo in repos:
        fetch("GET", f"{API}/repos/{repo}/stats/contributors", None)
    per_repo: dict[str, list[int]] = {}
    for repo in repos:
        try:
            per_repo[repo] = list(_contributor_totals(fetch, repo, login, retries, wait))
        except StillComputing:
            if not previous or repo not in previous:
                raise
            print(f"warning: {repo} still computing; reusing last totals")
            per_repo[repo] = previous[repo]
    commits, adds, dels = (sum(v[i] for v in per_repo.values()) for i in range(3))

    return Stats(
        repos=user["repositories"]["totalCount"],
        contributed=user["repositoriesContributedTo"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        followers=user["followers"]["totalCount"],
        commits=commits,
        contributions_1y=user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        additions=adds,
        deletions=dels,
        per_repo=per_repo,
    )


def load_cache(path: Path) -> Stats | None:
    try:
        return Stats(**json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return None


def save_cache(path: Path, stats: Stats) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(stats), indent=2) + "\n", encoding="utf-8")


def get_stats(login: str, cache: Path, fetch: Fetch | None = None, **kw) -> tuple[Stats, bool]:
    """Fresh stats (and refresh the cache), or the cached snapshot on failure.

    Returns (stats, fresh). Raises StatsError only if both sources fail.
    """
    if fetch is None:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        fetch = _http(token) if token else None
    if fetch is not None:
        cached = load_cache(cache)
        try:
            stats = fetch_stats(login, fetch, previous=cached.per_repo if cached else None, **kw)
            save_cache(cache, stats)
            return stats, True
        except (StatsError, OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as e:
            print(f"warning: live stats failed ({e}); using cache")
    cached = load_cache(cache)
    if cached is None:
        raise StatsError("no live stats and no cache")
    return cached, False
