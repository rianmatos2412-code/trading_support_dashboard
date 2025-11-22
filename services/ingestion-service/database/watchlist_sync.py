"""
Watchlist synchronization service for soft-delete/hysteresis pattern

This module handles:
1. Daily sync of active watchlist with database symbols
2. Implements soft-delete (is_active flag) to preserve historical OHLCV data
3. Monthly cleanup of symbols inactive for >180 days
"""
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import List, Set, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import structlog

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

# Import from local modules (relative to ingestion-service root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.database import DatabaseManager
from database.repository import split_symbol_components

logger = structlog.get_logger(__name__)


def sync_watchlist(db: Session, watchlist_symbols: List[str]) -> Dict[str, int]:
    """
    Sync the watchlist with database symbols using soft-delete pattern.
    
    This function:
    - Sets is_active=True and removed_at=NULL for symbols in the watchlist
    - Sets is_active=False and removed_at=now() for symbols not in watchlist
    - Creates new Symbol rows if they don't exist yet
    - Preserves all historical OHLCV data (never hard-deletes)
    
    Args:
        db: Database session
        watchlist_symbols: List of symbol strings (e.g., ["BTCUSDT", "ETHUSDT", "PEPEUSDT"])
    
    Returns:
        Dictionary with sync statistics:
        {
            "activated": number of symbols activated/reactivated,
            "deactivated": number of symbols deactivated,
            "created": number of new symbols created,
            "total_active": total active symbols after sync
        }
    
    This function is idempotent - safe to call multiple times with same watchlist.
    """
    try:
        # Normalize watchlist symbols (uppercase, no duplicates)
        watchlist_set = {s.upper().strip() for s in watchlist_symbols if s}
        logger.info("watchlist_sync_starting", watchlist_count=len(watchlist_set))
        
        # Get current active symbols from database
        current_active_result = db.execute(
            text("""
                SELECT symbol_name, symbol_id, is_active
                FROM symbols
                WHERE is_active = TRUE
            """)
        ).fetchall()
        current_active = {row[0]: row[1] for row in current_active_result}
        
        # Get all existing symbols (including inactive) for lookup
        all_symbols_result = db.execute(
            text("""
                SELECT symbol_name, symbol_id, is_active
                FROM symbols
            """)
        ).fetchall()
        all_symbols_map = {row[0]: {"id": row[1], "is_active": row[2]} for row in all_symbols_result}
        
        stats = {
            "activated": 0,
            "deactivated": 0,
            "created": 0,
            "total_active": 0
        }
        
        current_time = datetime.now(timezone.utc)
        
        # Process symbols in watchlist
        for symbol in watchlist_set:
            if symbol in all_symbols_map:
                # Symbol exists - activate if needed
                symbol_info = all_symbols_map[symbol]
                if not symbol_info["is_active"]:
                    # Reactivate symbol
                    db.execute(
                        text("""
                            UPDATE symbols
                            SET is_active = TRUE,
                                removed_at = NULL,
                                updated_at = :updated_at
                            WHERE symbol_id = :symbol_id
                        """),
                        {
                            "symbol_id": symbol_info["id"],
                            "updated_at": current_time
                        }
                    )
                    stats["activated"] += 1
                    logger.debug("symbol_reactivated", symbol=symbol)
            else:
                # New symbol - create it
                base_asset, quote_asset = split_symbol_components(symbol)
                db.execute(
                    text("""
                        INSERT INTO symbols (symbol_name, base_asset, quote_asset, is_active, removed_at, created_at, updated_at)
                        VALUES (:symbol_name, :base_asset, :quote_asset, TRUE, NULL, :created_at, :updated_at)
                        ON CONFLICT (symbol_name) DO UPDATE SET
                            is_active = TRUE,
                            removed_at = NULL,
                            updated_at = EXCLUDED.updated_at
                    """),
                    {
                        "symbol_name": symbol,
                        "base_asset": base_asset,
                        "quote_asset": quote_asset,
                        "created_at": current_time,
                        "updated_at": current_time
                    }
                )
                stats["created"] += 1
                logger.debug("symbol_created", symbol=symbol)
        
        # Deactivate symbols not in watchlist
        symbols_to_deactivate = set(current_active.keys()) - watchlist_set
        if symbols_to_deactivate:
            db.execute(
                text("""
                    UPDATE symbols
                    SET is_active = FALSE,
                        removed_at = :removed_at,
                        updated_at = :updated_at
                    WHERE symbol_name = ANY(:symbol_names)
                    AND is_active = TRUE
                """),
                {
                    "symbol_names": list(symbols_to_deactivate),
                    "removed_at": current_time,
                    "updated_at": current_time
                }
            )
            stats["deactivated"] = len(symbols_to_deactivate)
            logger.info("symbols_deactivated", count=stats["deactivated"], symbols=list(symbols_to_deactivate))
        
        # Commit all changes
        db.commit()
        
        # Get final count of active symbols
        stats["total_active"] = db.execute(
            text("SELECT COUNT(*) FROM symbols WHERE is_active = TRUE")
        ).scalar()
        
        logger.info(
            "watchlist_sync_completed",
            activated=stats["activated"],
            deactivated=stats["deactivated"],
            created=stats["created"],
            total_active=stats["total_active"]
        )
        
        return stats
        
    except Exception as e:
        db.rollback()
        logger.error(
            "watchlist_sync_error",
            error=str(e),
            exc_info=True
        )
        raise


def get_active_symbols(db: Session) -> List[str]:
    """
    Get list of active symbol names.
    
    Args:
        db: Database session
    
    Returns:
        List of active symbol names (e.g., ["BTCUSDT", "ETHUSDT"])
    """
    try:
        result = db.execute(
            text("""
                SELECT symbol_name
                FROM symbols
                WHERE is_active = TRUE
                ORDER BY symbol_name
            """)
        ).fetchall()
        return [row[0] for row in result]
    except Exception as e:
        logger.error("get_active_symbols_error", error=str(e), exc_info=True)
        return []


def cleanup_old_inactive_symbols(
    db: Session,
    days_inactive: int = 180,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Permanently delete symbols and their OHLCV data that have been inactive for >N days.
    
    This is a hard-delete operation that removes:
    - Symbol rows
    - All OHLCV candles for those symbols
    - All market_data for those symbols
    - All strategy_alerts for those symbols
    
    WARNING: This operation is irreversible. Use dry_run=True to preview.
    
    Args:
        db: Database session
        days_inactive: Number of days a symbol must be inactive before deletion (default: 180)
        dry_run: If True, only return statistics without deleting (default: False)
    
    Returns:
        Dictionary with cleanup statistics:
        {
            "symbols_to_delete": number of symbols that would be deleted,
            "ohlcv_rows_to_delete": number of OHLCV rows that would be deleted,
            "market_data_rows_to_delete": number of market_data rows that would be deleted,
            "strategy_alerts_to_delete": number of strategy_alerts that would be deleted,
            "deleted": actual number deleted (0 if dry_run=True)
        }
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        
        logger.info(
            "cleanup_starting",
            days_inactive=days_inactive,
            cutoff_date=cutoff_date.isoformat(),
            dry_run=dry_run
        )
        
        # Find symbols to delete
        symbols_to_delete_result = db.execute(
            text("""
                SELECT symbol_id, symbol_name, removed_at
                FROM symbols
                WHERE is_active = FALSE
                AND removed_at IS NOT NULL
                AND removed_at < :cutoff_date
            """),
            {"cutoff_date": cutoff_date}
        ).fetchall()
        
        if not symbols_to_delete_result:
            logger.info("cleanup_no_symbols_to_delete")
            return {
                "symbols_to_delete": 0,
                "ohlcv_rows_to_delete": 0,
                "market_data_rows_to_delete": 0,
                "strategy_alerts_to_delete": 0,
                "deleted": 0
            }
        
        symbol_ids = [row[0] for row in symbols_to_delete_result]
        symbol_names = [row[1] for row in symbols_to_delete_result]
        
        logger.info(
            "cleanup_symbols_found",
            count=len(symbol_ids),
            symbols=symbol_names[:10]  # Log first 10
        )
        
        # Count rows to be deleted
        ohlcv_count = db.execute(
            text("""
                SELECT COUNT(*)
                FROM ohlcv_candles
                WHERE symbol_id = ANY(:symbol_ids)
            """),
            {"symbol_ids": symbol_ids}
        ).scalar()
        
        market_data_count = db.execute(
            text("""
                SELECT COUNT(*)
                FROM market_data
                WHERE symbol_id = ANY(:symbol_ids)
            """),
            {"symbol_ids": symbol_ids}
        ).scalar()
        
        strategy_alerts_count = db.execute(
            text("""
                SELECT COUNT(*)
                FROM strategy_alerts
                WHERE symbol_id = ANY(:symbol_ids)
            """),
            {"symbol_ids": symbol_ids}
        ).scalar()
        
        stats = {
            "symbols_to_delete": len(symbol_ids),
            "ohlcv_rows_to_delete": ohlcv_count or 0,
            "market_data_rows_to_delete": market_data_count or 0,
            "strategy_alerts_to_delete": strategy_alerts_count or 0,
            "deleted": 0
        }
        
        if dry_run:
            logger.info("cleanup_dry_run_complete", stats=stats)
            return stats
        
        # Perform actual deletion (in correct order due to foreign keys)
        # 1. Delete strategy_alerts
        if strategy_alerts_count > 0:
            db.execute(
                text("""
                    DELETE FROM strategy_alerts
                    WHERE symbol_id = ANY(:symbol_ids)
                """),
                {"symbol_ids": symbol_ids}
            )
            logger.info("cleanup_deleted_strategy_alerts", count=strategy_alerts_count)
        
        # 2. Delete market_data
        if market_data_count > 0:
            db.execute(
                text("""
                    DELETE FROM market_data
                    WHERE symbol_id = ANY(:symbol_ids)
                """),
                {"symbol_ids": symbol_ids}
            )
            logger.info("cleanup_deleted_market_data", count=market_data_count)
        
        # 3. Delete ohlcv_candles
        if ohlcv_count > 0:
            db.execute(
                text("""
                    DELETE FROM ohlcv_candles
                    WHERE symbol_id = ANY(:symbol_ids)
                """),
                {"symbol_ids": symbol_ids}
            )
            logger.info("cleanup_deleted_ohlcv", count=ohlcv_count)
        
        # 4. Delete symbols (last, due to foreign key references)
        db.execute(
            text("""
                DELETE FROM symbols
                WHERE symbol_id = ANY(:symbol_ids)
            """),
            {"symbol_ids": symbol_ids}
        )
        logger.info("cleanup_deleted_symbols", count=len(symbol_ids))
        
        # Commit all deletions
        db.commit()
        
        stats["deleted"] = len(symbol_ids)
        
        logger.info(
            "cleanup_completed",
            symbols_deleted=stats["deleted"],
            ohlcv_deleted=stats["ohlcv_rows_to_delete"],
            market_data_deleted=stats["market_data_rows_to_delete"],
            strategy_alerts_deleted=stats["strategy_alerts_to_delete"]
        )
        
        return stats
        
    except Exception as e:
        db.rollback()
        logger.error(
            "cleanup_error",
            error=str(e),
            exc_info=True
        )
        raise

