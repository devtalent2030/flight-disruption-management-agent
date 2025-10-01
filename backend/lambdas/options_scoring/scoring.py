def score_option(opt: dict) -> int:
    score = 0
    score += 50 if opt.get("stops", 1) == 0 else 0
    score += 20 if opt.get("same_cabin", False) else 0
    score += 20 if opt.get("mct_ok", False) else 0
    diff = opt.get("arrival_diff_min", 120)
    score += max(0, 20 - min(diff, 20))
    return score
