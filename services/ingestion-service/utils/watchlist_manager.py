"""
Watchlist management utilities

This module provides functions to:
1. Get the current watchlist from ingestion results
2. Run daily watchlist sync
3. Run monthly cleanup
"""
import sys
import os
import asyncio
from typing import List
import structlog

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.database import DatabaseManager
from database.watchlist_sync import sync_watchlist, cleanup_old_inactive_symbols, get_active_symbols
from services.binance_service import BinanceIngestionService
from services.coingecko_service import CoinGeckoIngestionService

logger = structlog.get_logger(__name__)


async def get_current_watchlist() -> List[str]:
    """
    Get the current watchlist by running the ingestion process.
    
    This fetches the enriched assets from Binance perpetuals + CoinGecko,
    which represents the current active watchlist.
    
    Returns:
        List of symbol strings (e.g., ["BTCUSDT", "ETHUSDT", "PEPEUSDT"])
    """
    logger.info("fetching_current_watchlist")
    
    async with BinanceIngestionService() as binance_service:
        async with CoinGeckoIngestionService() as coingecko_service:
            # Get enriched assets (this is our watchlist)
            enriched_assets = await coingecko_service.ingest_from_binance_perpetuals(
                binance_service=binance_service
            )
            
            # Extract symbol names
            watchlist = [
                asset.get("_binance_symbol")
                for asset in enriched_assets
                if asset.get("_binance_symbol")
            ]
            
            logger.info("watchlist_fetched", count=len(watchlist))
            return watchlist


async def daily_watchlist_sync():
    """
    Daily watchlist synchronization task.
    
    This should be run once per day (e.g., via cron or scheduler) to:
    1. Get the current watchlist from ingestion
    2. Sync with database (activate/deactivate symbols)
    3. Preserve all historical OHLCV data
    """
    logger.info("daily_watchlist_sync_starting")
    
    try:
        # Get current watchlist
        watchlist = await get_current_watchlist()
        
        if not watchlist:
            logger.warning("daily_sync_empty_watchlist")
            return
        
        # Sync with database
        with DatabaseManager() as db:
            stats = sync_watchlist(db, watchlist)
            logger.info("daily_sync_completed", stats=stats)
            
    except Exception as e:
        logger.error("daily_sync_error", error=str(e), exc_info=True)
        raise


def monthly_cleanup(days_inactive: int = 180, dry_run: bool = False):
    """
    Monthly cleanup task for old inactive symbols.
    
    This should be run once per month (e.g., via cron) to permanently delete
    symbols and their data that have been inactive for >N days.
    
    Args:
        days_inactive: Number of days a symbol must be inactive (default: 180)
        dry_run: If True, only preview what would be deleted (default: False)
    """
    logger.info("monthly_cleanup_starting", days_inactive=days_inactive, dry_run=dry_run)
    
    try:
        with DatabaseManager() as db:
            stats = cleanup_old_inactive_symbols(db, days_inactive=days_inactive, dry_run=dry_run)
            logger.info("monthly_cleanup_completed", stats=stats)
            return stats
    except Exception as e:
        logger.error("monthly_cleanup_error", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Watchlist management utilities")
    parser.add_argument(
        "action",
        choices=["sync", "cleanup", "list-active"],
        help="Action to perform: sync (daily), cleanup (monthly), or list-active"
    )
    parser.add_argument(
        "--days-inactive",
        type=int,
        default=180,
        help="Days inactive for cleanup (default: 180)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleanup without deleting (only for cleanup action)"
    )
    
    args = parser.parse_args()
    
    if args.action == "sync":
        asyncio.run(daily_watchlist_sync())
    elif args.action == "cleanup":
        monthly_cleanup(days_inactive=args.days_inactive, dry_run=args.dry_run)
    elif args.action == "list-active":
        with DatabaseManager() as db:
            active = get_active_symbols(db)
            print(f"Active symbols ({len(active)}):")
            for symbol in active:
                print(f"  - {symbol}")

