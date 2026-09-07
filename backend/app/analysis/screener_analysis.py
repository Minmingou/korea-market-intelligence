def calculate_streak(net_buys: list[float | None]) -> int:
    """연속 순매수 일수. net_buys[0]이 가장 최신 날짜라고 가정하고, 최신부터
    거슬러 올라가며 연속으로 양수(순매수)인 일수를 센다. None(N/A)이나 0 이하를
    만나면 그 지점에서 멈춘다(끊긴 뒤의 값을 지어내지 않음).
    """
    streak = 0
    for value in net_buys:
        if value is None or value <= 0:
            break
        streak += 1
    return streak


def is_ma_aligned(closes: list[float], windows: tuple[int, ...] = (5, 20, 60)) -> bool:
    """이동평균 정배열(단기선이 장기선보다 위) 여부.

    closes는 날짜 오름차순(과거 -> 최신)이어야 한다. 가장 긴 윈도우만큼 데이터가
    없으면 판단할 수 없으므로 False를 반환한다(부족한 데이터로 지어내지 않음).
    """
    if len(closes) < max(windows):
        return False
    averages = [sum(closes[-w:]) / w for w in windows]
    return all(averages[i] > averages[i + 1] for i in range(len(averages) - 1))


def score_candidate(
    *,
    foreign_streak: int,
    institution_streak: int,
    ma_aligned: bool,
    volume_ratio: float | None,
    streak_threshold: int = 3,
    volume_surge_threshold: float = 1.5,
) -> tuple[int, list[str]]:
    """수급(외국인/기관 연속 순매수) + 기술적(이동평균 정배열/거래량 급증) 신호를
    조합해 0~4점으로 점수를 매기고, 어떤 조건이 맞았는지 사람이 읽을 수 있는
    문구로 함께 반환한다 - 왜 이 종목이 뽑혔는지 화면에서 바로 알 수 있어야
    "참고할만한" 스크리너가 된다(근거 없는 블랙박스 점수를 지양).
    """
    score = 0
    signals: list[str] = []

    if foreign_streak >= streak_threshold:
        score += 1
        signals.append(f"외국인 {foreign_streak}일 연속 순매수")
    if institution_streak >= streak_threshold:
        score += 1
        signals.append(f"기관 {institution_streak}일 연속 순매수")
    if ma_aligned:
        score += 1
        signals.append("이동평균 정배열(5>20>60)")
    if volume_ratio is not None and volume_ratio >= volume_surge_threshold:
        score += 1
        signals.append(f"거래량 급증({volume_ratio:.1f}배)")

    return score, signals
