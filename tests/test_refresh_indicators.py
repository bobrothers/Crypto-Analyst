# tests/test_refresh_indicators.py
# ---------------------------------------------------------------
# Unit tests for scripts/refresh_indicators.py
#
# Requires:
#   pytest
#   pytest-asyncio
#   aioresponses          # mocks aiohttp requests
#
# To run:
#   pytest -q
# ---------------------------------------------------------------

import os
import json
import shutil
import asyncio
from datetime import datetime

import pytest
from aioresponses import aioresponses

# Import the module under test
import sys
sys.path.append("scripts")               # so pytest finds the module
from refresh_indicators import (         # noqa: E402
    fetch_cbbi,
    fetch_rainbow_bands,
    fetch_pi_cycle,
    save_indicator,
    get_signal_from_value,
    DATA_DIR,
)

# ----------  Helpers / Fixtures  --------------------------------


@pytest.fixture(autouse=True)
def _clean_data_dir(tmp_path, monkeypatch):
    """
    Point DATA_DIR to a temporary path for every test
    and wipe it afterwards.
    """
    monkeypatch.setattr("refresh_indicators.DATA_DIR", tmp_path)
    yield
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def event_loop():
    """
    pytest-asyncio uses the event_loop fixture; we override it
    so each test gets a fresh loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ----------  Tests for each fetcher  ----------------------------

@pytest.mark.asyncio
async def test_fetch_cbbi_success():
    mock_json = {"score": 0.87}

    with aioresponses() as m:
        m.get(
            "https://ccbitcoinindex.appspot.com/api/score",
            payload=mock_json,
            status=200,
        )

        async with asyncio.Semaphore():  # dummy context mgr
            async with m:  # noqa: SIM117
                async with m._patch._patcher._patched_session() as session:
                    result = await fetch_cbbi(session)

    assert result["name"] == "CBBI"
    assert result["value"] == pytest.approx(0.87)
    assert result["signal"] == "bearish"


@pytest.mark.asyncio
async def test_fetch_rainbow_bands_success():
    # CSV header + one row (date, price, band1 .. band8)
    csv_body = "Date,Price,Band1,Band2,Band3,Band4,Band5,Band6,Band7,Band8\n" \
               "2025-05-20,55000,10000,20000,30000,40000,50000,60000,70000,80000"

    with aioresponses() as m:
        m.get(
            "https://api.blockchaincenter.net/v1/rainbow",
            body=csv_body,
            status=200,
            headers={"Content-Type": "text/csv"},
        )

        async with m._patch._patcher._patched_session() as session:
            result = await fetch_rainbow_bands(session)

    assert result["name"] == "Rainbow Bands"
    assert result["value"] == 6          # price sits in 6th band
    assert result["signal"] == "neutral"


@pytest.mark.asyncio
async def test_fetch_pi_cycle_placeholder():
    with aioresponses():                 # no HTTP call expected
        async with asyncio.Semaphore():
            async with asyncio.Semaphore():  # dummy
                async with asyncio.Semaphore():
                    async with asyncio.Semaphore():
                        async with asyncio.Semaphore():
                            async with asyncio.Semaphore():
                                async with asyncio.Semaphore():
                                    async with asyncio.Semaphore():
                                        async with asyncio.Semaphore():
                                            # call the placeholder
                                            result = await fetch_pi_cycle(None)

    assert result["name"] == "Pi Cycle"
    assert 0.5 <= result["value"] <= 0.8
    assert result["signal"] in ("bullish", "neutral", "bearish")


# ----------  Test save_indicator  -------------------------------

def test_save_indicator_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr("refresh_indicators.DATA_DIR", tmp_path)

    sample = {
        "name": "CBBI",
        "timestamp": datetime.utcnow().isoformat(),
        "value": 0.42,
        "signal": "bullish"
    }

    save_indicator(sample, date_str="2025-05-20")

    expected_path = tmp_path / "cbbi" / "2025-05-20.json"
    assert expected_path.exists()

    with open(expected_path) as fp:
        loaded = json.load(fp)

    assert loaded == sample


# ----------  Edge-case: signal helper  --------------------------

@pytest.mark.parametrize(
    "indicator,value,expected",
    [
        ("cbbi", 0.9, "bearish"),
        ("cbbi", 0.1, "bullish"),
        ("rainbow_bands", 1, "bullish"),
        ("rainbow_bands", 8, "bearish"),
        ("pi_cycle", 0.96, "bearish"),
        ("pi_cycle", 0.4, "bullish"),
    ],
)
def test_get_signal_from_value(indicator, value, expected):
    assert get_signal_from_value(indicator, value) == expected
