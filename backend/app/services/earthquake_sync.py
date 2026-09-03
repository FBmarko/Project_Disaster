import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.afad.client import AfadClient
from app.integrations.afad.mapping import TURKEY_CONTEXT_BBOX
from app.integrations.afad.parser import parse_afad_event_list
from app.repositories.earthquake_event import EarthquakeEventRepository

logger = logging.getLogger("afet360.services.earthquake_sync")


@dataclass
class SyncStatistics:
    """Summary metrics of an earthquake synchronization run."""

    total_received: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0


class EarthquakeSyncService:
    """Service handling idempotent synchronization of seismic events from AFAD."""

    def __init__(
        self,
        session: Session,
        client: AfadClient | None = None,
    ) -> None:
        self.session = session
        self.client = client or AfadClient()
        self.repository = EarthquakeEventRepository(session)

    def sync_events(
        self,
        raw_events: list[dict[str, Any]],
        batch_size: int = 250,
    ) -> SyncStatistics:
        """Parse, validate, and idempotently upsert raw AFAD events in batches."""
        total_received = len(raw_events)
        valid_records, skipped, failed = parse_afad_event_list(raw_events)

        total_inserted = 0
        total_updated = 0
        total_unchanged = 0

        for i in range(0, len(valid_records), batch_size):
            chunk = valid_records[i : i + batch_size]
            with self.session.begin_nested():
                ins, upd, unc = self.repository.upsert_batch(chunk)
            total_inserted += ins
            total_updated += upd
            total_unchanged += unc

        self.session.flush()

        logger.info(
            "Sync: %d recvd, %d ins, %d upd, %d unc, %d failed",
            total_received,
            total_inserted,
            total_updated,
            total_unchanged,
            failed,
        )

        return SyncStatistics(
            total_received=total_received,
            inserted=total_inserted,
            updated=total_updated,
            unchanged=total_unchanged,
            skipped=skipped,
            failed=failed,
        )

    def sync_from_afad(
        self,
        start: datetime | str,
        end: datetime | str,
        min_magnitude: float = 5.0,
        bbox: tuple[float, float, float, float] | None = TURKEY_CONTEXT_BBOX,
        page_size: int = 100,
        max_pages: int = 50,
        max_events: int = 2000,
    ) -> SyncStatistics:
        """Fetch events directly from AFAD Web Service and synchronize into database."""
        logger.info(
            "Fetching earthquakes from AFAD (start=%s, end=%s, min_mag=%.1f)...",
            start,
            end,
            min_magnitude,
        )
        raw_events = self.client.fetch_all_events(
            start=start,
            end=end,
            min_magnitude=min_magnitude,
            bbox=bbox,
            page_size=page_size,
            max_pages=max_pages,
            max_events=max_events,
        )

        return self.sync_events(raw_events)
