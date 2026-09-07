from app.analysis.screener_analysis import calculate_streak, is_ma_aligned, score_candidate


def test_calculate_streak_counts_consecutive_positive_from_latest():
    assert calculate_streak([100, 50, 30, -10, 200]) == 3


def test_calculate_streak_stops_at_none():
    assert calculate_streak([100, None, 50]) == 1


def test_calculate_streak_zero_when_latest_is_negative():
    assert calculate_streak([-10, 100, 100]) == 0


def test_calculate_streak_empty_list():
    assert calculate_streak([]) == 0


def test_is_ma_aligned_true_for_upward_stacked_averages():
    # 최근 5개는 높고 예전 값들은 낮게 -> MA5 > MA20 > MA60이 되도록 구성
    closes = [10.0] * 55 + [20.0] * 5
    assert is_ma_aligned(closes, windows=(5, 20, 60)) is True


def test_is_ma_aligned_false_when_not_enough_data():
    assert is_ma_aligned([10.0] * 59, windows=(5, 20, 60)) is False


def test_is_ma_aligned_false_when_downward():
    closes = [20.0] * 55 + [10.0] * 5
    assert is_ma_aligned(closes, windows=(5, 20, 60)) is False


def test_score_candidate_accumulates_and_explains_each_signal():
    score, signals = score_candidate(
        foreign_streak=4,
        institution_streak=1,
        ma_aligned=True,
        volume_ratio=2.0,
    )
    assert score == 3
    assert signals == [
        "외국인 4일 연속 순매수",
        "이동평균 정배열(5>20>60)",
        "거래량 급증(2.0배)",
    ]


def test_score_candidate_zero_when_nothing_matches():
    score, signals = score_candidate(
        foreign_streak=1,
        institution_streak=1,
        ma_aligned=False,
        volume_ratio=0.8,
    )
    assert score == 0
    assert signals == []


def test_score_candidate_handles_none_volume_ratio():
    score, signals = score_candidate(
        foreign_streak=0,
        institution_streak=0,
        ma_aligned=False,
        volume_ratio=None,
    )
    assert score == 0
    assert signals == []
