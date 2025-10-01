
from lambdas.options_scoring.scoring import score_option

def test_direct_better_than_connect():
    a = {"stops": 0, "same_cabin": True, "mct_ok": True, "arrival_diff_min": 10}
    b = {"stops": 1, "same_cabin": True, "mct_ok": True, "arrival_diff_min": 0}
    assert score_option(a) > score_option(b)
