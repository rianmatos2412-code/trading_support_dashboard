"""
Example queries for working with active/inactive symbols

These are example queries showing how to:
1. Get only active symbols
2. Query OHLCV data for active symbols only
3. Get inactive symbols with their removal dates
4. Query historical data for reactivated symbols
"""
from sqlalchemy import text
from shared.database import DatabaseManager

# ============================================================================
# EXAMPLE 1: Get all active symbols
# ============================================================================
def example_get_active_symbols():
    """Get list of all active symbols"""
    with DatabaseManager() as db:
        result = db.execute(
            text("""
                SELECT symbol_id, symbol_name, base_asset, quote_asset, created_at
                FROM symbols
                WHERE is_active = TRUE
                ORDER BY symbol_name
            """)
        ).fetchall()
        return [dict(row) for row in result]


# ============================================================================
# EXAMPLE 2: Get OHLCV data for active symbols only
# ============================================================================
def example_get_ohlcv_for_active_symbols(timeframe: str = "1h", limit: int = 100):
    """Get latest OHLCV candles for all active symbols"""
    with DatabaseManager() as db:
        result = db.execute(
            text("""
                SELECT 
                    s.symbol_name,
                    t.tf_name as timeframe,
                    oc.timestamp,
                    oc.open,
                    oc.high,
                    oc.low,
                    oc.close,
                    oc.volume
                FROM ohlcv_candles oc
                INNER JOIN symbols s ON oc.symbol_id = s.symbol_id
                INNER JOIN timeframe t ON oc.timeframe_id = t.timeframe_id
                WHERE s.is_active = TRUE
                AND t.tf_name = :timeframe
                ORDER BY oc.timestamp DESC
                LIMIT :limit
            """),
            {"timeframe": timeframe, "limit": limit}
        ).fetchall()
        return [dict(row) for row in result]


# ============================================================================
# EXAMPLE 3: Get inactive symbols with removal dates
# ============================================================================
def example_get_inactive_symbols():
    """Get list of inactive symbols with their removal dates"""
    with DatabaseManager() as db:
        result = db.execute(
            text("""
                SELECT 
                    symbol_id,
                    symbol_name,
                    removed_at,
                    EXTRACT(EPOCH FROM (NOW() - removed_at)) / 86400 as days_inactive
                FROM symbols
                WHERE is_active = FALSE
                AND removed_at IS NOT NULL
                ORDER BY removed_at DESC
            """)
        ).fetchall()
        return [dict(row) for row in result]


# ============================================================================
# EXAMPLE 4: Get symbols that were reactivated (came back to watchlist)
# ============================================================================
def example_get_reactivated_symbols():
    """Get symbols that were reactivated (had removed_at but now is_active=True)"""
    with DatabaseManager() as db:
        result = db.execute(
            text("""
                SELECT 
                    symbol_id,
                    symbol_name,
                    removed_at,
                    updated_at
                FROM symbols
                WHERE is_active = TRUE
                AND removed_at IS NOT NULL
                ORDER BY updated_at DESC
            """)
        ).fetchall()
        return [dict(row) for row in result]


# ============================================================================
# EXAMPLE 5: Get market data for active symbols only
# ============================================================================
def example_get_market_data_for_active_symbols():
    """Get latest market data for all active symbols"""
    with DatabaseManager() as db:
        result = db.execute(
            text("""
                SELECT DISTINCT ON (s.symbol_id)
                    s.symbol_name,
                    md.market_cap,
                    md.price,
                    md.volume_24h,
                    md.circulating_supply,
                    md.timestamp
                FROM market_data md
                INNER JOIN symbols s ON md.symbol_id = s.symbol_id
                WHERE s.is_active = TRUE
                ORDER BY s.symbol_id, md.timestamp DESC
            """)
        ).fetchall()
        return [dict(row) for row in result]


# ============================================================================
# EXAMPLE 6: Count symbols by status
# ============================================================================
def example_get_symbol_stats():
    """Get statistics about active/inactive symbols"""
    with DatabaseManager() as db:
        result = db.execute(
            text("""
                SELECT 
                    COUNT(*) FILTER (WHERE is_active = TRUE) as active_count,
                    COUNT(*) FILTER (WHERE is_active = FALSE) as inactive_count,
                    COUNT(*) FILTER (WHERE is_active = FALSE AND removed_at IS NOT NULL) as inactive_with_date,
                    COUNT(*) as total_count
                FROM symbols
            """)
        ).fetchone()
        return dict(result)

