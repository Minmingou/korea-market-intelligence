def score_value_candidate(
    *,
    per: float | None,
    pbr: float | None,
    roe: float | None,
    debt_ratio: float | None,
    operating_margin: float | None,
    per_threshold: float = 12.0,
    pbr_threshold: float = 1.2,
    roe_threshold: float = 10.0,
    debt_ratio_threshold: float = 100.0,
    operating_margin_threshold: float = 10.0,
) -> tuple[int, list[str]]:
    """저평가(PER/PBR 낮음) + 우량(ROE/영업이익률 높음, 부채비율 낮음) 신호를
    조합해 0~5점으로 점수를 매기고, 어떤 조건이 맞았는지 사람이 읽을 수 있는
    문구로 함께 반환한다. 수급 스크리너(screener_analysis.score_candidate)와
    같은 이유로 근거 없는 블랙박스 점수를 지양한다.

    값이 None(N/A)인 지표는 조건 미달로 취급하지 않고 단순히 건너뛴다 - 데이터가
    없는 것과 조건을 만족하지 못한 것은 다르다.
    """
    score = 0
    signals: list[str] = []

    if per is not None and 0 < per < per_threshold:
        score += 1
        signals.append(f"PER {per:.1f}배 (저평가)")
    if pbr is not None and 0 < pbr < pbr_threshold:
        score += 1
        signals.append(f"PBR {pbr:.1f}배 (저평가)")
    if roe is not None and roe >= roe_threshold:
        score += 1
        signals.append(f"ROE {roe:.1f}% (고수익성)")
    if operating_margin is not None and operating_margin >= operating_margin_threshold:
        score += 1
        signals.append(f"영업이익률 {operating_margin:.1f}% (고수익성)")
    if debt_ratio is not None and debt_ratio < debt_ratio_threshold:
        score += 1
        signals.append(f"부채비율 {debt_ratio:.0f}% (재무 안정)")

    return score, signals
