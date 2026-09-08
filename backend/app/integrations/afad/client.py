import logging
import ssl
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.integrations.afad.mapping import (
    AFAD_DEFAULT_BASE_URL,
    DEFAULT_MAX_HTTP_REQUESTS,
    DEFAULT_MAX_PAGES_PER_WINDOW,
    DEFAULT_MIN_MAGNITUDE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_WINDOW_DAYS,
)

logger = logging.getLogger("afet360.integrations.afad")

DEFAULT_USER_AGENT = "AFET360/0.1.0 (University disaster preparedness project)"


class AfadClientError(Exception):
    """Base exception for AFAD client errors."""


def to_utc_datetime(val: datetime | str) -> datetime:
    """Coerce datetime or ISO string to timezone-aware UTC datetime."""
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=UTC)
        return val.astimezone(UTC)
    s = str(val).strip().replace("Z", "+00:00").replace(" ", "T")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def generate_date_windows(
    start: datetime,
    end: datetime,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into sequential windows of at most window_days."""
    if start >= end:
        return []
    if window_days <= 0:
        return [(start, end)]

    windows: list[tuple[datetime, datetime]] = []
    current_start = start
    step = timedelta(days=window_days)

    while current_start < end:
        current_end = min(current_start + step, end)
        windows.append((current_start, current_end))
        current_start = current_end

    return windows


class AfadClient:
    """HTTP client for querying the official AFAD Event Web Service."""

    def __init__(
        self,
        base_url: str = AFAD_DEFAULT_BASE_URL,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._custom_client = client

    def _create_client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            verify=ssl.create_default_context(),
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    def fetch_events(
        self,
        start: datetime | str,
        end: datetime | str,
        min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
        http_client: httpx.Client | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch a single page of earthquake events from AFAD."""
        start_str = (
            start.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(start, datetime)
            else str(start)
        )
        end_str = (
            end.strftime("%Y-%m-%d %H:%M:%S") if isinstance(end, datetime) else str(end)
        )

        params: dict[str, Any] = {
            "start": start_str,
            "end": end_str,
            "minmag": str(min_magnitude),
            "limit": str(limit),
            "offset": str(offset),
            "format": "json",
            "orderby": "timedesc",
        }

        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
            params["minlon"] = str(min_lon)
            params["maxlon"] = str(max_lon)
            params["minlat"] = str(min_lat)
            params["maxlat"] = str(max_lat)

        url = self.base_url
        attempt = 0

        client = http_client or self._custom_client or self._create_client()
        should_close = http_client is None and self._custom_client is None

        try:
            while attempt < self.max_retries:
                attempt += 1
                try:
                    response = client.get(url, params=params)

                    if response.status_code >= 500:
                        logger.warning(
                            "AFAD server error HTTP %d (attempt %d/%d)",
                            response.status_code,
                            attempt,
                            self.max_retries,
                        )
                    else:
                        response.raise_for_status()
                        data = response.json()
                        if isinstance(data, list):
                            return data
                        if isinstance(data, dict) and "message" in data:
                            logger.info("AFAD returned message: %s", data["message"])
                            return []
                        return []

                except (httpx.TransportError, httpx.TimeoutException) as exc:
                    logger.warning(
                        "Network error connecting to AFAD (attempt %d/%d): %s",
                        attempt,
                        self.max_retries,
                        exc,
                    )
                except httpx.HTTPStatusError as exc:
                    # Do not retry 4xx errors
                    if exc.response.status_code < 500:
                        msg = (
                            f"AFAD client error HTTP {exc.response.status_code}: "
                            f"{exc.response.text}"
                        )
                        raise AfadClientError(msg) from exc

                if attempt < self.max_retries:
                    sleep_sec = self.backoff_factor * (2 ** (attempt - 1))
                    time.sleep(sleep_sec)

            raise AfadClientError(
                f"Failed to fetch AFAD events after {self.max_retries} attempts"
            )
        finally:
            if should_close:
                client.close()

    def fetch_all_events(
        self,
        start: datetime | str,
        end: datetime | str,
        min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
        bbox: tuple[float, float, float, float] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES_PER_WINDOW,
        max_events: int = 2000,
        http_client: httpx.Client | None = None,
    ) -> list[dict[str, Any]]:
        """Paginate through AFAD event results up to configured safety boundaries."""
        all_events: list[dict[str, Any]] = []
        offset = 0
        page = 0

        client = http_client or self._custom_client or self._create_client()
        should_close = http_client is None and self._custom_client is None

        try:
            while page < max_pages and len(all_events) < max_events:
                page += 1
                logger.info(
                    "Fetching AFAD events (page %d, offset %d, limit %d)...",
                    page,
                    offset,
                    page_size,
                )

                batch = self.fetch_events(
                    start=start,
                    end=end,
                    min_magnitude=min_magnitude,
                    bbox=bbox,
                    limit=page_size,
                    offset=offset,
                    http_client=client,
                )

                if not batch:
                    break

                all_events.extend(batch)

                if len(batch) < page_size:
                    break

                offset += len(batch)

            return all_events[:max_events]
        finally:
            if should_close:
                client.close()

    def fetch_all_events_chunked(
        self,
        start: datetime | str,
        end: datetime | str,
        min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
        bbox: tuple[float, float, float, float] | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages_per_window: int = DEFAULT_MAX_PAGES_PER_WINDOW,
        max_events: int = 5000,
        max_requests: int = DEFAULT_MAX_HTTP_REQUESTS,
    ) -> list[dict[str, Any]]:
        """Query AFAD over sequential date windows, respecting safety bounds."""
        start_dt = to_utc_datetime(start)
        end_dt = to_utc_datetime(end)
        windows = generate_date_windows(start_dt, end_dt, window_days)

        if not windows:
            return []

        client = self._custom_client or self._create_client()
        should_close = self._custom_client is None

        all_events: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        total_requests = 0

        try:
            for w_idx, (w_start, w_end) in enumerate(windows, 1):
                if total_requests >= max_requests or len(all_events) >= max_events:
                    logger.info(
                        "Stop limit reached (requests=%d/%d, events=%d/%d).",
                        total_requests,
                        max_requests,
                        len(all_events),
                        max_events,
                    )
                    break

                offset = 0
                page = 0

                while page < max_pages_per_window and len(all_events) < max_events:
                    if total_requests >= max_requests:
                        logger.warning(
                            "Max HTTP request budget (%d) reached. Stopping.",
                            max_requests,
                        )
                        break

                    page += 1
                    total_requests += 1

                    logger.info(
                        "Chunk [%d/%d] %s -> %s (page %d, offset %d, reqs %d)...",
                        w_idx,
                        len(windows),
                        w_start.strftime("%Y-%m-%d"),
                        w_end.strftime("%Y-%m-%d"),
                        page,
                        offset,
                        total_requests,
                    )

                    batch = self.fetch_events(
                        start=w_start,
                        end=w_end,
                        min_magnitude=min_magnitude,
                        bbox=bbox,
                        limit=page_size,
                        offset=offset,
                        http_client=client,
                    )

                    if not batch:
                        break

                    for event in batch:
                        eid = str(
                            event.get("eventID") or event.get("EventID") or ""
                        ).strip()
                        if eid and eid in seen_ids:
                            continue
                        if eid:
                            seen_ids.add(eid)
                        all_events.append(event)
                        if len(all_events) >= max_events:
                            break

                    if len(batch) < page_size or len(all_events) >= max_events:
                        break

                    offset += len(batch)

            return all_events[:max_events]
        finally:
            if should_close:
                client.close()
