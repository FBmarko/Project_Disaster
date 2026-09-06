import argparse
import logging
import sys
from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.integrations.afad.mapping import (
    AFAD_ATTRIBUTION_NOTICE,
    AFAD_ATTRIBUTION_SOURCE,
    DEFAULT_COVERAGE_YEARS,
    DEFAULT_MAX_HTTP_REQUESTS,
    DEFAULT_MIN_MAGNITUDE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_WINDOW_DAYS,
    TURKEY_CONTEXT_BBOX,
    get_project_coverage_start,
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
        required=False,
        default=None,
        help="Start date/time (default: rolling previous 10 years UTC)",
    )
    parser.add_argument(
        "--end",
        required=False,
        default=None,
        help="End date/time (default: current UTC timestamp)",
    )
    parser.add_argument(
        "--min-magnitude",
        type=float,
        default=DEFAULT_MIN_MAGNITUDE,
        help=f"Minimum seismic magnitude threshold [default: {DEFAULT_MIN_MAGNITUDE}]",
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
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help=f"Sequential date chunk size in days [default: {DEFAULT_WINDOW_DAYS}]",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=(
            f"Number of events per AFAD API request page [default: {DEFAULT_PAGE_SIZE}]"
        ),
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=DEFAULT_MAX_HTTP_REQUESTS,
        help=f"Maximum HTTP requests allowed [default: {DEFAULT_MAX_HTTP_REQUESTS}]",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=5000,
        help="Maximum total events to synchronize in this run [default: 5000]",
    )

    args = parser.parse_args()

    # Determine coverage window
    now_utc = datetime.now(UTC)
    if args.end:
        end_str = args.end
    else:
        end_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    if args.start:
        start_str = args.start
    else:
        start_dt = get_project_coverage_start(now_utc, years=DEFAULT_COVERAGE_YEARS)
        start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")

    bbox = TURKEY_CONTEXT_BBOX if args.scope == "turkey-context" else None

    logger.info("Connecting to database...")
    with SessionLocal() as session:
        sync_service = EarthquakeSyncService(session)

        try:
            stats = sync_service.sync_from_afad(
                start=start_str,
                end=end_str,
                min_magnitude=args.min_magnitude,
                bbox=bbox,
                window_days=args.window_days,
                page_size=args.page_size,
                max_events=args.max_events,
                max_requests=args.max_requests,
            )
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("AFAD synchronization failed: %s", exc)
            sys.exit(1)

    print("\n" + "=" * 45)
    print("      AFAD EARTHQUAKE SYNC SUMMARY")
    print("=" * 45)
    print(f"Time Window           : {start_str} -> {end_str}")
    print(f"Min Magnitude         : {args.min_magnitude}")
    print(f"Chunk Window Days     : {args.window_days}")
    print(f"Max Requests Budget   : {args.max_requests}")
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
