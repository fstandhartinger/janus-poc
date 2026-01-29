"""Arena ELO calculation helpers."""

from collections import defaultdict
from typing import Iterable, Literal, TypedDict


ArenaWinner = Literal["A", "B", "tie", "both_bad"]


class ArenaVoteLike(TypedDict):
    model_a: str
    model_b: str
    winner: ArenaWinner


def update_elo(
    rating_a: float,
    rating_b: float,
    winner: ArenaWinner,
    k: float = 32.0,
) -> tuple[float, float]:
    """Update ELO ratings based on match result."""
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 - expected_a

    if winner == "A":
        score_a, score_b = 1.0, 0.0
    elif winner == "B":
        score_a, score_b = 0.0, 1.0
    else:  # tie or both_bad treated as tie for rating purposes
        score_a, score_b = 0.5, 0.5

    new_rating_a = rating_a + k * (score_a - expected_a)
    new_rating_b = rating_b + k * (score_b - expected_b)

    return new_rating_a, new_rating_b


def compute_leaderboard(votes: Iterable[ArenaVoteLike]) -> list[dict]:
    """Compute arena leaderboard from all votes."""
    ratings: dict[str, float] = defaultdict(lambda: 1500.0)
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0})

    for vote in votes:
        model_a = vote["model_a"]
        model_b = vote["model_b"]
        winner = vote["winner"]

        if winner in ("A", "B", "tie"):
            ratings[model_a], ratings[model_b] = update_elo(
                ratings[model_a],
                ratings[model_b],
                winner,
            )

        if winner == "A":
            stats[model_a]["wins"] += 1
            stats[model_b]["losses"] += 1
        elif winner == "B":
            stats[model_b]["wins"] += 1
            stats[model_a]["losses"] += 1
        else:
            stats[model_a]["ties"] += 1
            stats[model_b]["ties"] += 1

    leaderboard = []
    for model, elo in ratings.items():
        record = stats.get(model, {"wins": 0, "losses": 0, "ties": 0})
        matches = record["wins"] + record["losses"] + record["ties"]
        leaderboard.append(
            {
                "model": model,
                "elo": float(elo),
                "wins": record["wins"],
                "losses": record["losses"],
                "ties": record["ties"],
                "matches": matches,
            }
        )

    return sorted(leaderboard, key=lambda entry: entry["elo"], reverse=True)
