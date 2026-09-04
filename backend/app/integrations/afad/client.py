import logging
import time
from datetime import datetime
from typing import Any

import httpx

from app.integrations.afad.mapping import AFAD_DEFAULT_BASE_URL

logger = logging.getLogger("afet360.integrations.afad")

DEFAULT_USER_AGENT = "AFET360/0.1.0 (University disaster preparedness project)"


class AfadClientError(Exception):
    """Base exception for AFAD client errors."""


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
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    def fetch_events(
        self,
        start: datetime | str,
        end: datetime | str,
        min_magnitude: float = 5.0,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 100,
        offset: int = 0,
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
        }

        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
            params["minlon"] = str(min_lon)
            params["maxlon"] = str(max_lon)
            params["minlat"] = str(min_lat)
            params["maxlat"] = str(max_lat)

        url = self.base_url
        attempt = 0

        client = self._custom_client or self._create_client()
        should_close = self._custom_client is None

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
        min_magnitude: float = 5.0,
        bbox: tuple[float, float, float, float] | None = None,
        page_size: int = 100,
        max_pages: int = 50,
        max_events: int = 2000,
    ) -> list[dict[str, Any]]:
        """Paginate through AFAD event results up to configured safety boundaries."""
        all_events: list[dict[str, Any]] = []
        offset = 0
        page = 0

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
            )

            if not batch:
                break

            all_events.extend(batch)

            if len(batch) < page_size:
                break

            offset += len(batch)

        return all_events[:max_events]
