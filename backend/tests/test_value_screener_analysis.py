from app.analysis.value_screener_analysis import score_value_candidate


def test_score_value_candidate_all_conditions_met():
    score, signals = score_value_candidate(
        per=8.0, pbr=1.0, roe=15.0, debt_ratio=50.0, operating_margin=12.0
    )
    assert score == 5
    assert signals == [
        "PER 8.0배 (저평가)",
        "PBR 1.0배 (저평가)",
        "ROE 15.0% (고수익성)",
        "영업이익률 12.0% (고수익성)",
        "부채비율 50% (재무 안정)",
    ]


def test_score_value_candidate_no_conditions_met():
    score, signals = score_value_candidate(
        per=30.0, pbr=3.0, roe=2.0, debt_ratio=200.0, operating_margin=1.0
    )
    assert score == 0
    assert signals == []


def test_score_value_candidate_none_values_are_skipped_not_penalized():
    score, signals = score_value_candidate(
        per=None, pbr=None, roe=None, debt_ratio=None, operating_margin=None
    )
    assert score == 0
    assert signals == []


def test_score_value_candidate_negative_per_or_pbr_does_not_count_as_undervalued():
    # 적자 기업의 PER/PBR이 음수여도 "저평가"로 잘못 인식하면 안 된다.
    score, signals = score_value_candidate(
        per=-5.0, pbr=-1.0, roe=None, debt_ratio=None, operating_margin=None
    )
    assert score == 0
    assert signals == []


def test_score_value_candidate_partial_signals():
    score, signals = score_value_candidate(
        per=10.0, pbr=2.0, roe=20.0, debt_ratio=150.0, operating_margin=5.0
    )
    assert score == 2
    assert signals == ["PER 10.0배 (저평가)", "ROE 20.0% (고수익성)"]
