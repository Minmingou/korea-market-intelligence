from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.services import market_service


@pytest.fixture(autouse=True)
def _reset_lock():
    # 이전 테스트가 실패로 끝나 락을 들고 있는 상태로 남지 않도록 보장한다.
    for lock in market_service._refresh_locks.values():
        if lock.locked():
            lock.release()
    yield
    for lock in market_service._refresh_locks.values():
        if lock.locked():
            lock.release()


@pytest.fixture(autouse=True)
def _restore_settings():
    original_mock = settings.use_mock_data
    original_interval = settings.kis_refresh_interval_seconds
    yield
    settings.use_mock_data = original_mock
    settings.kis_refresh_interval_seconds = original_interval


def _make_repo(is_fresh: bool, has_any: bool = True) -> MagicMock:
    repo = MagicMock()
    repo.is_fresh_since.return_value = is_fresh
    repo.has_any.return_value = has_any
    return repo


def test_freshness_cutoff_mock_mode_is_start_of_today():
    settings.use_mock_data = True
    now = datetime(2026, 9, 7, 15, 30, tzinfo=timezone.utc)
    assert market_service._freshness_cutoff(now, "KR") == datetime(
        2026, 9, 7, 0, 0, tzinfo=timezone.utc
    )


def test_freshness_cutoff_real_mode_is_interval_seconds_ago():
    settings.use_mock_data = False
    settings.kis_refresh_interval_seconds = 30
    now = datetime(2026, 9, 7, 15, 30, 45, tzinfo=timezone.utc)
    assert market_service._freshness_cutoff(now, "KR") == datetime(
        2026, 9, 7, 15, 30, 15, tzinfo=timezone.utc
    )


@patch("app.services.market_service.MarketRepository")
@patch("app.services.market_service.StockRepository")
def test_refresh_if_needed_skips_when_data_is_fresh(mock_stock_repo_cls, mock_market_repo_cls):
    mock_stock_repo_cls.return_value = _make_repo(is_fresh=True)
    mock_market_repo_cls.return_value = _make_repo(is_fresh=True)
    settings.use_mock_data = True

    with (
        patch("app.services.market_service._fetch_and_store") as fetch,
        patch("app.services.market_service.threading.Thread") as thread_cls,
    ):
        market_service.refresh_if_needed(db=MagicMock())

    fetch.assert_not_called()
    thread_cls.assert_not_called()


@patch("app.services.market_service.MarketRepository")
@patch("app.services.market_service.StockRepository")
def test_refresh_if_needed_mock_mode_fetches_synchronously(
    mock_stock_repo_cls, mock_market_repo_cls
):
    # Mock 모드는 데이터가 있어도(has_any=True) 항상 동기로 갱신한다 — 백그라운드
    # 분기는 실 KIS 전용이다.
    mock_stock_repo_cls.return_value = _make_repo(is_fresh=False, has_any=True)
    mock_market_repo_cls.return_value = _make_repo(is_fresh=False, has_any=True)
    settings.use_mock_data = True

    with (
        patch("app.services.market_service._fetch_and_store") as fetch,
        patch("app.services.market_service.threading.Thread") as thread_cls,
    ):
        market_service.refresh_if_needed(db=MagicMock())

    fetch.assert_called_once()
    thread_cls.assert_not_called()
    assert not market_service._refresh_locks["KR"].locked()


@patch("app.services.market_service.MarketRepository")
@patch("app.services.market_service.StockRepository")
def test_refresh_if_needed_real_kis_cold_start_fetches_synchronously(
    mock_stock_repo_cls, mock_market_repo_cls
):
    # 콜드스타트(has_any=False)는 반환할 기존 데이터가 없으므로 실 KIS라도 동기로 기다린다.
    mock_stock_repo_cls.return_value = _make_repo(is_fresh=False, has_any=False)
    mock_market_repo_cls.return_value = _make_repo(is_fresh=False, has_any=False)
    settings.use_mock_data = False

    with (
        patch("app.services.market_service._fetch_and_store") as fetch,
        patch("app.services.market_service.threading.Thread") as thread_cls,
    ):
        market_service.refresh_if_needed(db=MagicMock())

    fetch.assert_called_once()
    thread_cls.assert_not_called()
    assert not market_service._refresh_locks["KR"].locked()


@patch("app.services.market_service.MarketRepository")
@patch("app.services.market_service.StockRepository")
def test_refresh_if_needed_real_kis_warm_data_refreshes_in_background(
    mock_stock_repo_cls, mock_market_repo_cls
):
    mock_stock_repo_cls.return_value = _make_repo(is_fresh=False, has_any=True)
    mock_market_repo_cls.return_value = _make_repo(is_fresh=False, has_any=True)
    settings.use_mock_data = False

    with (
        patch("app.services.market_service._fetch_and_store") as fetch,
        patch("app.services.market_service.threading.Thread") as thread_cls,
    ):
        market_service.refresh_if_needed(db=MagicMock())

    fetch.assert_not_called()
    thread_cls.assert_called_once()
    _, kwargs = thread_cls.call_args
    assert kwargs["target"] == market_service._refresh_in_background
    assert kwargs["args"] == ("KR",)
    assert kwargs["daemon"] is True
    thread_cls.return_value.start.assert_called_once()
    # 백그라운드 스레드가 (mock이라) 실행되지 않았으니 락은 아직 반환되지 않은 상태다.
    assert market_service._refresh_locks["KR"].locked()


@patch("app.services.market_service.MarketRepository")
@patch("app.services.market_service.StockRepository")
def test_refresh_if_needed_single_flight_skips_when_lock_already_held(
    mock_stock_repo_cls, mock_market_repo_cls
):
    mock_stock_repo_cls.return_value = _make_repo(is_fresh=False)
    mock_market_repo_cls.return_value = _make_repo(is_fresh=False)
    settings.use_mock_data = True
    market_service._refresh_locks["KR"].acquire()

    with (
        patch("app.services.market_service._fetch_and_store") as fetch,
        patch("app.services.market_service.threading.Thread") as thread_cls,
    ):
        market_service.refresh_if_needed(db=MagicMock())

    fetch.assert_not_called()
    thread_cls.assert_not_called()


def test_fetch_and_store_swallows_client_errors():
    stock_repo = MagicMock()
    market_repo = MagicMock()

    with patch("app.services.market_service.get_market_data_client") as get_client:
        get_client.return_value.fetch_stocks.side_effect = RuntimeError("boom")
        market_service._fetch_and_store(stock_repo, market_repo, "KR")

    stock_repo.upsert_many.assert_not_called()
    market_repo.upsert_many.assert_not_called()


def test_fetch_and_store_upserts_on_success():
    stock_repo = MagicMock()
    market_repo = MagicMock()

    with patch("app.services.market_service.get_market_data_client") as get_client:
        get_client.return_value.fetch_stocks.return_value = ["stock"]
        get_client.return_value.fetch_market_indices.return_value = ["index"]
        market_service._fetch_and_store(stock_repo, market_repo, "KR")

    stock_repo.upsert_many.assert_called_once_with(["stock"])
    market_repo.upsert_many.assert_called_once_with(["index"])


def test_refresh_in_background_releases_lock_via_session_local():
    market_service._refresh_locks["KR"].acquire()

    with (
        patch("app.services.market_service.SessionLocal") as session_local,
        patch("app.services.market_service._fetch_and_store") as fetch,
    ):
        market_service._refresh_in_background("KR")

    fetch.assert_called_once()
    session_local.return_value.close.assert_called_once()
    assert not market_service._refresh_locks["KR"].locked()
