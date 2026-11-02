import itertools
import random
from uuid import uuid4

from santa.matching import allowed_recipients, feasibility, matching
from santa.schemas import EventData


def config(count, groups=()):
    people = [
        {"id": str(uuid4()), "name": f"Personne {i}", "email": f"person{i}@example.com"}
        for i in range(count)
    ]
    return EventData(
        participants=people,
        groups=[
            {
                "id": str(uuid4()),
                "name": f"Groupe {i}",
                "members": [people[index]["id"] for index in members],
            }
            for i, members in enumerate(groups)
        ],
    )


def assert_valid(data, result):
    assert result is not None
    edges = allowed_recipients(data)
    assert set(result) == set(edges)
    assert set(result.values()) == set(edges)
    assert all(recipient in edges[giver] for giver, recipient in result.items())


def test_small_and_large_draws():
    for count in (2, 3, 5, 200):
        data = config(count)
        for _ in range(3):
            assert_valid(data, matching(data, randomize=True))


def test_couples_and_overlapping_groups():
    for data in (config(4, [(0, 1), (2, 3)]), config(6, [(0, 1), (1, 2)])):
        assert feasibility(data)["possible"]
        assert_valid(data, matching(data, randomize=True))


def test_impossible_and_stranded():
    assert matching(config(0)) is None
    assert matching(config(1)) is None
    assert not feasibility(config(3, [(0, 1, 2)]))["possible"]
    # Three givers can only choose from the other two people.
    data = config(5, [(0, 1, 2)])
    assert all(allowed_recipients(data).values())
    assert matching(data) is None
    assert not feasibility(data)["possible"]


def test_exact_verdict_matches_exhaustive_search():
    rng = random.Random(42)
    for count in range(2, 7):
        for _ in range(12):
            groups = [
                (first, second)
                for first in range(count)
                for second in range(first + 1, count)
                if rng.random() < 0.3
            ]
            data = config(count, groups)
            edges = allowed_recipients(data)
            expected = any(
                all(
                    recipient in edges[giver]
                    for giver, recipient in zip(edges, permutation, strict=True)
                )
                for permutation in itertools.permutations(edges)
            )
            assert feasibility(data)["possible"] == expected
            assert (matching(data, randomize=True) is not None) == expected
