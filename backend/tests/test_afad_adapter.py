import json
from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.integrations.afad import (
    AFAD_ATTRIBUTION_NOTICE,
    AFAD_ATTRIBUTION_SOURCE,
    AfadClient,
    AfadClientError,
    coords_to_point_wkt,
    parse_afad_datetime,
    parse_afad_event,
    parse_afad_event_list,
)
from app.schemas.earthquake_event import EarthquakeEventCreate

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "afad_events_sample.json"


def test_parse_afad_datetime_utc() -> None:
    """Verify AFAD datetime strings parse into timezone-aware UTC datetimes."""
    dt_str = "2023-02-06T01:17:32"
    dt = parse_afad_datetime(dt_str)

    assert dt.year == 2023
    assert dt.month == 2
    assert dt.day == 6
    assert dt.hour == 1
    assert dt.minute == 17
    assert dt.second == 32
    assert dt.tzinfo == UTC

    # Space separated format
    dt2 = parse_afad_datetime("2024-01-06 11:53:31")
    assert dt2.tzinfo == UTC
    assert dt2.hour == 11


def test_parse_afad_datetime_invalid() -> None:
    """Verify invalid date strings raise ValueError."""
    with pytest.raises(ValueError):
        parse_afad_datetime("")

    with pytest.raises(ValueError):
        parse_afad_datetime("not-a-date")


def test_coords_to_point_wkt() -> None:
    """Verify Point WKT uses canonical EPSG:4326 (longitude latitude) order."""
    wkt = coords_to_point_wkt(28.9784, 41.0082)
    assert wkt == "SRID=4326;POINT(28.9784 41.0082)"


def test_parse_afad_event_valid() -> None:
    """Verify parsing a complete valid AFAD event item."""
    raw = {
        "eventID": "543428",
        "location": "Pazarcık (Kahramanmaraş)",
        "latitude": "37.27728",
        "longitude": "37.03996",
        "depth": "8.6",
        "type": "MW",
        "magnitude": "7.7",
        "country": "Türkiye",
        "province": "Kahramanmaraş",
        "district": "Pazarcık",
        "neighborhood": "Karahüyük",
        "date": "2023-02-06T01:17:32",
        "isEventUpdate": True,
        "lastUpdateDate": "2023-02-06T09:46:31.642742",
        "rms": "1.92",
    }

    event = parse_afad_event(raw)
    assert event is not None
    assert isinstance(event, EarthquakeEventCreate)
    assert event.source == "AFAD"
    assert event.source_event_id == "543428"
    assert event.latitude == 37.27728
    assert event.longitude == 37.03996
    assert event.depth_km == 8.6
    assert event.magnitude == 7.7
    assert event.magnitude_type == "MW"
    assert event.location_name == "Pazarcık (Kahramanmaraş)"
    assert event.province == "Kahramanmaraş"
    assert event.is_updated is True
    assert event.last_update_at is None
    assert event.source_properties["lastUpdateDate"] == "2023-02-06T09:46:31.642742"
    assert event.source_properties["rms"] == "1.92"


def test_parse_afad_event_missing_id() -> None:
    """Verify events missing eventID are safely rejected."""
    raw = {
        "location": "Izmir",
        "latitude": "38.0",
        "longitude": "27.0",
        "depth": "10.0",
        "magnitude": "5.0",
        "date": "2024-01-01T00:00:00",
    }
    assert parse_afad_event(raw) is None


def test_parse_afad_event_invalid_coordinates() -> None:
    """Verify out-of-range coordinates are rejected."""
    raw = {
        "eventID": "999",
        "latitude": "95.0",  # Out of range (-90 to 90)
        "longitude": "30.0",
        "depth": "10.0",
        "magnitude": "5.0",
        "date": "2024-01-01T00:00:00",
    }
    assert parse_afad_event(raw) is None


def test_parse_afad_event_negative_depth() -> None:
    """Verify negative depth is rejected."""
    raw = {
        "eventID": "999",
        "latitude": "38.0",
        "longitude": "30.0",
        "depth": "-5.0",
        "magnitude": "5.0",
        "date": "2024-01-01T00:00:00",
    }
    assert parse_afad_event(raw) is None


def test_parse_afad_fixture_sample() -> None:
    """Verify parsing the sample fixtures file."""
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    events, skipped, failed = parse_afad_event_list(data)
    assert len(events) == 5
    assert skipped == 0
    assert failed == 0

    assert events[0].source_event_id == "543428"
    assert events[0].magnitude == 7.7
    assert events[1].source_event_id == "543593"
    assert events[1].magnitude == 7.6
    assert events[4].source_event_id == "699999"
    assert events[4].country is None


def test_attribution_constants() -> None:
    """Verify AFAD official attribution constants are defined."""
    assert "AFAD" in AFAD_ATTRIBUTION_SOURCE
    assert "İçişleri Bakanlığı" in AFAD_ATTRIBUTION_SOURCE
    assert "Event Web Servisi" in AFAD_ATTRIBUTION_NOTICE


def test_afad_client_retries_on_500() -> None:
    """Verify AfadClient retries on HTTP 500 server errors up to max_retries."""
    mock_transport = MagicMock()
    # Return 500 twice, then 200
    mock_resp_500 = httpx.Response(500, request=httpx.Request("GET", "https://test"))
    mock_resp_200 = httpx.Response(
        200,
        json=[
            {
                "eventID": "123",
                "date": "2024-01-01T00:00:00",
                "latitude": "38.0",
                "longitude": "27.0",
                "depth": "10.0",
                "magnitude": "5.0",
            }
        ],
        request=httpx.Request("GET", "https://test"),
    )
    mock_transport.handle_request.side_effect = [
        mock_resp_500,
        mock_resp_500,
        mock_resp_200,
    ]

    client = httpx.Client(transport=mock_transport)
    afad_client = AfadClient(
        base_url="https://test",
        max_retries=3,
        backoff_factor=0.01,
        client=client,
    )

    events = afad_client.fetch_events(
        start="2024-01-01",
        end="2024-01-02",
        min_magnitude=5.0,
    )
    assert len(events) == 1
    assert events[0]["eventID"] == "123"
    assert mock_transport.handle_request.call_count == 3


def test_afad_client_fails_after_max_retries() -> None:
    """Verify AfadClient raises AfadClientError when retries are exhausted."""
    mock_transport = MagicMock()
    mock_resp_500 = httpx.Response(500, request=httpx.Request("GET", "https://test"))
    mock_transport.handle_request.return_value = mock_resp_500

    client = httpx.Client(transport=mock_transport)
    afad_client = AfadClient(
        base_url="https://test",
        max_retries=2,
        backoff_factor=0.01,
        client=client,
    )

    with pytest.raises(AfadClientError):
        afad_client.fetch_events(start="2024-01-01", end="2024-01-02")


def test_afad_client_pagination_stop() -> None:
    """Verify fetch_all_events stops when batch size is less than page_size."""
    afad_client = AfadClient()
    mock_batch_1 = [{"eventID": "1"}, {"eventID": "2"}]
    mock_batch_2 = [{"eventID": "3"}]  # Size 1 < page_size 2 => termination

    with patch.object(
        afad_client, "fetch_events", side_effect=[mock_batch_1, mock_batch_2]
    ):
        events = afad_client.fetch_all_events(
            start="2024-01-01",
            end="2024-01-02",
            page_size=2,
            max_pages=5,
        )
        assert len(events) == 3
        assert [e["eventID"] for e in events] == ["1", "2", "3"]
