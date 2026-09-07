from app.clients.stock_master import (
    StockMasterEntry,
    _parse_mst,
    build_code_market_index,
    search_stock_master,
)


def _mst_line(code: str, name: str, part2_width: int) -> str:
    # KIS 마스터 파일의 한 줄 = part1(단축코드 9 + 표준코드 12 + 한글명 나머지) + part2(고정폭 꼬리).
    part1 = code.ljust(9) + "KR7005930003" + name
    part2 = "0" * part2_width
    return part1 + part2


def test_parse_mst_extracts_code_and_name_for_kospi():
    line = _mst_line("005930", "삼성전자", 228)
    entries = _parse_mst(line.encode("cp949"), "KOSPI")
    assert entries == [StockMasterEntry(stock_code="005930", stock_name="삼성전자", market="KOSPI")]


def test_parse_mst_extracts_code_and_name_for_kosdaq():
    line = _mst_line("247540", "에코프로비엠", 222)
    entries = _parse_mst(line.encode("cp949"), "KOSDAQ")
    assert entries == [
        StockMasterEntry(stock_code="247540", stock_name="에코프로비엠", market="KOSDAQ")
    ]


def test_parse_mst_skips_lines_shorter_than_part2_width():
    entries = _parse_mst(b"too short\n", "KOSPI")
    assert entries == []


def test_search_stock_master_prioritizes_exact_code_over_name_matches():
    entries = [
        StockMasterEntry("005935", "이건005930이 이름에 들어간 종목", "KOSPI"),
        StockMasterEntry("005930", "삼성전자", "KOSPI"),
    ]

    result = search_stock_master("005930", entries, limit=10)
    assert result[0].stock_code == "005930"  # 코드 완전일치가 이름에 코드가 섞인 종목보다 우선
    assert result[1].stock_code == "005935"


def test_search_stock_master_prioritizes_name_prefix_over_name_contains():
    entries = [
        StockMasterEntry("005935", "우선주삼성전자", "KOSPI"),  # 이름 "포함"
        StockMasterEntry("005930", "삼성전자", "KOSPI"),  # 이름 "시작"
    ]

    result = search_stock_master("삼성전자", entries, limit=10)
    assert result[0].stock_code == "005930"
    assert result[1].stock_code == "005935"


def test_search_stock_master_matches_by_name_substring():
    entries = [
        StockMasterEntry("000660", "SK하이닉스", "KOSPI"),
        StockMasterEntry("005930", "삼성전자", "KOSPI"),
    ]
    result = search_stock_master("하이닉스", entries, limit=10)
    assert [e.stock_code for e in result] == ["000660"]


def test_search_stock_master_returns_empty_for_blank_query():
    assert search_stock_master("   ", [StockMasterEntry("005930", "삼성전자", "KOSPI")]) == []


def test_search_stock_master_respects_limit():
    entries = [StockMasterEntry(f"{i:06d}", f"테스트{i}", "KOSPI") for i in range(20)]
    result = search_stock_master("테스트", entries, limit=5)
    assert len(result) == 5


def test_build_code_market_index_maps_code_to_market():
    entries = [
        StockMasterEntry("005930", "삼성전자", "KOSPI"),
        StockMasterEntry("247540", "에코프로비엠", "KOSDAQ"),
    ]
    index = build_code_market_index(entries)
    assert index == {"005930": "KOSPI", "247540": "KOSDAQ"}
