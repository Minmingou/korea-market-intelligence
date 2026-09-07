def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["database"] == "ok"


def test_market_overview(client):
    res = client.get("/api/market/overview")
    assert res.status_code == 200
    body = res.json()
    assert body["kospi"]["market"] == "KOSPI"
    assert body["kosdaq"]["market"] == "KOSDAQ"
    assert "updated_at" in body


def test_list_stocks_returns_at_least_50(client):
    res = client.get("/api/stocks")
    assert res.status_code == 200
    stocks = res.json()
    assert len(stocks) >= 50
    assert all(s["data_source"] == "mock" for s in stocks)


def test_list_stocks_filtered_by_market(client):
    res = client.get("/api/stocks", params={"market": "KOSDAQ"})
    assert res.status_code == 200
    stocks = res.json()
    assert len(stocks) > 0
    assert all(s["market"] == "KOSDAQ" for s in stocks)


def test_get_single_stock(client):
    res = client.get("/api/stocks/005930")
    assert res.status_code == 200
    assert res.json()["stock_code"] == "005930"


def test_get_unknown_stock_returns_404(client):
    res = client.get("/api/stocks/999999")
    assert res.status_code == 404


def test_market_movers_top_gainers_sorted_desc(client):
    res = client.get("/api/stocks/movers", params={"category": "top_gainers", "limit": 5})
    assert res.status_code == 200
    body = res.json()
    change_rates = [item["change_rate"] for item in body["items"]]
    assert change_rates == sorted(change_rates, reverse=True)


def test_market_movers_unknown_category_is_rejected(client):
    res = client.get("/api/stocks/movers", params={"category": "not_a_real_category"})
    assert res.status_code == 422


def test_sectors_endpoint(client):
    res = client.get("/api/sectors")
    assert res.status_code == 200
    sectors = res.json()
    assert len(sectors) > 0
    assert sum(s["stock_count"] for s in sectors) >= 50


def test_money_flow_endpoint(client):
    res = client.get("/api/flows")
    assert res.status_code == 200
    body = res.json()
    assert "totals" in body
    assert len(body["foreign_top_buy"]) > 0


def test_company_financials_endpoint(client):
    res = client.get("/api/stocks/005930/financials")
    assert res.status_code == 200
    body = res.json()
    assert body["stock_code"] == "005930"
    assert body["data_source"] == "mock"
    assert body["net_income"] is not None
    assert body["per"] is not None


def test_company_financials_unknown_stock_returns_404(client):
    res = client.get("/api/stocks/999999/financials")
    assert res.status_code == 404


def test_disclosures_endpoint(client):
    res = client.get("/api/stocks/005930/disclosures", params={"count": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["stock_code"] == "005930"
    assert body["data_source"] == "mock"
    assert len(body["items"]) <= 5
    assert all(item["url"] is None for item in body["items"])


def test_disclosures_unknown_stock_returns_empty_list(client):
    res = client.get("/api/stocks/999999/disclosures")
    assert res.status_code == 200
    assert res.json()["items"] == []


def test_events_endpoint(client):
    res = client.get("/api/events", params={"count": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["data_source"] == "mock"
    assert len(body["items"]) <= 5
    rcept_dates = [item["rcept_dt"] for item in body["items"]]
    assert rcept_dates == sorted(rcept_dates, reverse=True)
    assert all("stock_name" in item for item in body["items"])


def test_news_endpoint(client):
    res = client.get("/api/stocks/005930/news", params={"count": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["stock_code"] == "005930"
    assert body["data_source"] == "mock"
    assert len(body["items"]) <= 5
    assert all(item["url"] is None for item in body["items"])
    assert all(item["title"] for item in body["items"])


def test_news_unknown_stock_returns_empty_list(client):
    res = client.get("/api/stocks/999999/news")
    assert res.status_code == 200
    assert res.json()["items"] == []


def test_market_brief_endpoint(client):
    res = client.get("/api/market/brief")
    assert res.status_code == 200
    body = res.json()
    assert body["data_source"] == "mock"
    assert "KOSPI" in body["summary"]


def test_stock_brief_endpoint(client):
    res = client.get("/api/stocks/005930/brief")
    assert res.status_code == 200
    body = res.json()
    assert body["stock_code"] == "005930"
    assert body["data_source"] == "mock"
    assert "삼성전자" in body["summary"]


def test_stock_brief_unknown_stock_returns_404(client):
    res = client.get("/api/stocks/999999/brief")
    assert res.status_code == 404


def _patch_stock_master(monkeypatch):
    from app.clients.stock_master import StockMasterEntry

    monkeypatch.setattr(
        "app.services.stock_service.get_stock_master",
        lambda: [
            StockMasterEntry("005930", "삼성전자", "KOSPI"),
            StockMasterEntry("005935", "삼성전자우", "KOSPI"),
            StockMasterEntry("000660", "SK하이닉스", "KOSPI"),
        ],
    )


def test_search_stocks_matches_by_name(client, monkeypatch):
    _patch_stock_master(monkeypatch)
    res = client.get("/api/stocks/search", params={"q": "삼성전자"})
    assert res.status_code == 200
    body = res.json()
    assert body["query"] == "삼성전자"
    codes = [item["stock_code"] for item in body["items"]]
    assert "005930" in codes
    assert "005935" in codes
    assert "000660" not in codes


def test_search_stocks_matches_by_code(client, monkeypatch):
    _patch_stock_master(monkeypatch)
    res = client.get("/api/stocks/search", params={"q": "000660"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert items[0]["stock_code"] == "000660"


def test_search_stocks_requires_query_param(client):
    res = client.get("/api/stocks/search")
    assert res.status_code == 422


def test_stock_chart_endpoint_returns_ohlcv_bars(client):
    res = client.get("/api/stocks/005930/chart", params={"period": "D", "count": 10})
    assert res.status_code == 200
    body = res.json()
    assert body["stock_code"] == "005930"
    assert body["period"] == "D"
    assert len(body["items"]) == 10
    bar = body["items"][0]
    assert set(bar) == {"date", "open", "high", "low", "close", "volume"}


def test_stock_chart_endpoint_unknown_stock_returns_404(client):
    res = client.get("/api/stocks/999999/chart")
    assert res.status_code == 404


def test_stock_chart_endpoint_rejects_invalid_period(client):
    res = client.get("/api/stocks/005930/chart", params={"period": "X"})
    assert res.status_code == 422
