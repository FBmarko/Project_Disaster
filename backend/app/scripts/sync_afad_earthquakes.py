import argparse
import logging
import sys

from app.db.session import SessionLocal
from app.integrations.afad.mapping import (
    AFAD_ATTRIBUTION_NOTICE,
    AFAD_ATTRIBUTION_SOURCE,
    TURKEY_CONTEXT_BBOX,
)
from app.services.earthquake_sync import EarthquakeSyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("afet360.sync_afad_earthquakes")


def main() -> None:
    """Developer CLI command to synchronize earthquake events from AFAD."""
    parser = argparse.ArgumentParser(
        description="Synchronize seismic events from AFAD into AFET360."
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date/time (e.g. '2023-01-01' or '2023-01-01 00:00:00')",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date/time (e.g. '2024-01-01' or '2024-01-01 00:00:00')",
    )
    parser.add_argument(
        "--min-magnitude",
        type=float,
        default=5.0,
        help="Minimum seismic magnitude threshold [default: 5.0]",
    )
    parser.add_argument(
        "--scope",
        choices=["turkey-context", "all"],
        default="turkey-context",
        help=(
            "Geographic bounding scope "
            "(turkey-context: 24-46°E, 34-44°N; all: global) "
            "[default: turkey-context]"
        ),
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Number of events per AFAD API request page [default: 100]",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=2000,
        help="Maximum total events to synchronize in this run [default: 2000]",
    )

    args = parser.parse_args()

    bbox = TURKEY_CONTEXT_BBOX if args.scope == "turkey-context" else None

    logger.info("Connecting to database...")
    with SessionLocal() as session:
        sync_service = EarthquakeSyncService(session)

        try:
            stats = sync_service.sync_from_afad(
                start=args.start,
                end=args.end,
                min_magnitude=args.min_magnitude,
                bbox=bbox,
                page_size=args.page_size,
                max_events=args.max_events,
            )
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("AFAD synchronization failed: %s", exc)
            sys.exit(1)

    print("\n" + "=" * 45)
    print("      AFAD EARTHQUAKE SYNC SUMMARY")
    print("=" * 45)
    print(f"Time Window           : {args.start} -> {args.end}")
    print(f"Min Magnitude         : {args.min_magnitude}")
    print(f"Geographic Scope      : {args.scope}")
    print(f"Total Events Received : {stats.total_received}")
    print(f"Inserted (New)        : {stats.inserted}")
    print(f"Updated (Revised)     : {stats.updated}")
    print(f"Unchanged (Identical) : {stats.unchanged}")
    print(f"Skipped / Failed      : {stats.skipped} / {stats.failed}")
    print("=" * 45)
    print(f"Source      : {AFAD_ATTRIBUTION_SOURCE}")
    print(f"Attribution : {AFAD_ATTRIBUTION_NOTICE}")
    print("=" * 45 + "\n")


if __name__ == "__main__":
    main()
