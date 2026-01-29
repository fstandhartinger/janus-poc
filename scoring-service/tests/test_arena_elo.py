from scoring_service.arena_elo import compute_leaderboard, update_elo


def test_update_elo_rewards_winner():
    rating_a, rating_b = update_elo(1500, 1500, "A", k=32.0)
    assert rating_a > 1500
    assert rating_b < 1500


def test_compute_leaderboard_tracks_stats():
    votes = [
        {"model_a": "alpha", "model_b": "beta", "winner": "A"},
        {"model_a": "alpha", "model_b": "beta", "winner": "A"},
        {"model_a": "alpha", "model_b": "gamma", "winner": "B"},
    ]
    leaderboard = compute_leaderboard(votes)
    ratings = {entry["model"]: entry["elo"] for entry in leaderboard}
    assert ratings["alpha"] > ratings["beta"]
    alpha_entry = next(entry for entry in leaderboard if entry["model"] == "alpha")
    assert alpha_entry["matches"] == 3
    assert alpha_entry["wins"] == 2
    assert alpha_entry["losses"] == 1
