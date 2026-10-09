import json

import pytest

from generator.stats import Stats, StatsError, fetch_stats, get_stats, load_cache, save_cache

GRAPHQL = {
    "data": {
        "user": {
            "followers": {"totalCount": 3},
            "repositories": {
                "totalCount": 2,
                "nodes": [
                    {"nameWithOwner": "me/a", "stargazerCount": 5},
                    {"nameWithOwner": "me/b", "stargazerCount": 1},
                ],
            },
            "repositoriesContributedTo": {"totalCount": 1, "nodes": [{"nameWithOwner": "org/c"}]},
            "contributionsCollection": {"contributionCalendar": {"totalContributions": 77}},
        }
    }
}


def contributors(login, total, adds, dels):
    return [
        {"author": {"login": "someone-else"}, "total": 999, "weeks": [{"a": 999, "d": 999}]},
        {"author": {"login": login}, "total": total, "weeks": [{"a": adds, "d": dels}, {"a": 1, "d": 0}]},
    ]


class FakeAPI:
    def __init__(self, routes):
        self.routes = routes  # url suffix -> list of (status, body), consumed in order
        self.calls = []

    def __call__(self, method, url, body):
        self.calls.append(url)
        for suffix, responses in self.routes.items():
            if url.endswith(suffix):
                return responses.pop(0) if len(responses) > 1 else responses[0]
        raise AssertionError(f"unexpected {url}")


def happy_api():
    return FakeAPI({
        "/graphql": [(200, GRAPHQL)],
        "/repos/me/a/stats/contributors": [(202, None), (200, contributors("Me", 10, 100, 20))],
        "/repos/me/b/stats/contributors": [(204, None)],
        "/repos/org/c/stats/contributors": [(200, contributors("me", 4, 50, 5))],
    })


def test_fetch_stats_aggregates_and_retries_202():
    s = fetch_stats("me", happy_api(), wait=0)
    assert s == Stats(repos=2, contributed=1, stars=6, followers=3, commits=14,
                      contributions_1y=77, additions=152, deletions=25)
    assert s.loc == 127


def test_fetch_stats_gives_up_when_still_computing():
    api = FakeAPI({"/graphql": [(200, GRAPHQL)], "/stats/contributors": [(202, None)]})
    with pytest.raises(StatsError, match="still computing"):
        fetch_stats("me", api, retries=3, wait=0)


def test_fetch_stats_rejects_graphql_errors():
    api = FakeAPI({"/graphql": [(200, {"errors": [{"message": "nope"}]})]})
    with pytest.raises(StatsError):
        fetch_stats("me", api, wait=0)


def test_get_stats_refreshes_cache(tmp_path):
    cache = tmp_path / "stats.json"
    s, fresh = get_stats("me", cache, fetch=happy_api(), wait=0)
    assert fresh and load_cache(cache) == s


def test_get_stats_falls_back_to_cache(tmp_path):
    cache = tmp_path / "stats.json"
    old = Stats(1, 0, 0, 0, 5, 9, 10, 2)
    save_cache(cache, old)
    broken = FakeAPI({"/graphql": [(502, None)]})
    s, fresh = get_stats("me", cache, fetch=broken, wait=0)
    assert (s, fresh) == (old, False)
    assert json.loads(cache.read_text())["commits"] == 5  # cache untouched


def test_get_stats_fails_loudly_with_nothing(tmp_path):
    broken = FakeAPI({"/graphql": [(502, None)]})
    with pytest.raises(StatsError):
        get_stats("me", tmp_path / "missing.json", fetch=broken, wait=0)


def test_corrupt_cache_is_ignored(tmp_path):
    cache = tmp_path / "stats.json"
    cache.write_text("{not json")
    assert load_cache(cache) is None


def slow_c_api():
    return FakeAPI({
        "/graphql": [(200, GRAPHQL)],
        "/repos/me/a/stats/contributors": [(200, contributors("me", 10, 100, 20))],
        "/repos/me/b/stats/contributors": [(204, None)],
        "/repos/org/c/stats/contributors": [(202, None)],
    })


def test_slow_repo_reuses_its_last_totals():
    s = fetch_stats("me", slow_c_api(), retries=2, wait=0, previous={"org/c": [7, 70, 7]})
    assert (s.commits, s.additions, s.deletions) == (17, 171, 27)
    assert s.per_repo["org/c"] == [7, 70, 7]


def test_slow_repo_without_history_fails_the_live_run():
    with pytest.raises(StatsError):
        fetch_stats("me", slow_c_api(), retries=2, wait=0, previous={})


def test_per_repo_totals_round_trip_through_cache(tmp_path):
    cache = tmp_path / "stats.json"
    get_stats("me", cache, fetch=happy_api(), wait=0)
    assert load_cache(cache).per_repo["me/a"] == [10, 101, 20]
    # next day org/c is slow: the cached per-repo value fills in, run stays live
    s, fresh = get_stats("me", cache, fetch=slow_c_api(), retries=2, wait=0)
    assert fresh and s.per_repo["org/c"] == [4, 51, 5]


def test_flaky_network_errors_fall_back_to_cache(tmp_path):
    import http.client

    cache = tmp_path / "stats.json"
    save_cache(cache, Stats(1, 0, 0, 0, 5, 9, 10, 2))

    def flaky(*_):
        raise http.client.IncompleteRead(b"")

    s, fresh = get_stats("me", cache, fetch=flaky, wait=0)
    assert not fresh and s.commits == 5


def test_loc_never_goes_negative():
    assert Stats(1, 0, 0, 0, 1, 1, additions=5, deletions=9).loc == 0
