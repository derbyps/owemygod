from eval.report import summarize


def test_summarize_rates():
    s = summarize([{"valid": True, "kind_ok": True, "exact": True, "early": False, "late": False},
                   {"valid": True, "kind_ok": True, "exact": False, "early": True, "late": False}])
    assert s == {"n": 2, "valid": 1.0, "kind_acc": 1.0, "exact": 0.5, "early": 0.5, "late": 0.0}


def test_summarize_empty():
    assert summarize([])["n"] == 0
