# Watchlist Soft-Delete / Hysteresis System

This document describes the soft-delete system for managing symbols that enter and leave the watchlist while preserving historical OHLCV data.

## Overview

The system implements an industry-standard soft-delete pattern with hysteresis:
- **Never hard-delete** OHLCV data when symbols leave the watchlist
- Use `is_active` flag to mark active/inactive symbols
- Use `removed_at` timestamp to track when symbols were removed
- Preserve all historical data for reactivated symbols
- Optional monthly cleanup for symbols inactive >180 days

## Database Schema

### New Columns Added to `symbols` Table

```sql
is_active BOOLEAN NOT NULL DEFAULT TRUE
removed_at TIMESTAMPTZ NULL
```

- `is_active`: `TRUE` for symbols currently in watchlist, `FALSE` for removed symbols
- `removed_at`: Timestamp when symbol was removed (NULL if active)

### Indexes

- `idx_symbols_is_active`: Partial index on `is_active = TRUE` for fast active symbol queries
- `idx_symbols_removed_at`: Partial index on `removed_at IS NOT NULL` for cleanup queries

## Migration

Run the migration to add the new columns:

```bash
psql -U trading_user -d trading_db -f database/migrations/002_add_symbol_soft_delete.sql
```

Or apply via your migration tool.

## Daily Watchlist Sync

### Purpose

Synchronize the current watchlist (from ingestion) with the database:
- Activate symbols that are in the watchlist
- Deactivate symbols that are not in the watchlist
- Create new symbols if they don't exist
- Preserve all historical OHLCV data

### Usage

```python
from database.watchlist_sync import sync_watchlist
from shared.database import DatabaseManager

# Get current watchlist (e.g., from ingestion results)
watchlist = ["BTCUSDT", "ETHUSDT", "PEPEUSDT", ...]

# Sync with database
with DatabaseManager() as db:
    stats = sync_watchlist(db, watchlist)
    print(f"Activated: {stats['activated']}")
    print(f"Deactivated: {stats['deactivated']}")
    print(f"Created: {stats['created']}")
    print(f"Total Active: {stats['total_active']}")
```

### Command Line

```bash
# Run daily sync
python -m services.ingestion-service.utils.watchlist_manager sync
```

### Integration with Ingestion

After ingestion completes, you can automatically sync:

```python
# In main.py or ingestion service
async def main():
    # ... run ingestion ...
    enriched_assets = await coingecko_service.ingest_from_binance_perpetuals(...)
    
    # Extract watchlist
    watchlist = [asset.get("_binance_symbol") for asset in enriched_assets]
    
    # Sync with database
    with DatabaseManager() as db:
        sync_watchlist(db, watchlist)
```

## Monthly Cleanup

### Purpose

Permanently delete symbols and their data that have been inactive for >180 days.

**WARNING**: This is a hard-delete operation. Use `dry_run=True` first to preview.

### Usage

```python
from database.watchlist_sync import cleanup_old_inactive_symbols
from shared.database import DatabaseManager

# Preview what would be deleted (dry run)
with DatabaseManager() as db:
    stats = cleanup_old_inactive_symbols(db, days_inactive=180, dry_run=True)
    print(f"Would delete {stats['symbols_to_delete']} symbols")
    print(f"Would delete {stats['ohlcv_rows_to_delete']} OHLCV rows")

# Actually delete (after reviewing dry run)
with DatabaseManager() as db:
    stats = cleanup_old_inactive_symbols(db, days_inactive=180, dry_run=False)
    print(f"Deleted {stats['deleted']} symbols")
```

### Command Line

```bash
# Preview cleanup (dry run)
python -m services.ingestion-service.utils.watchlist_manager cleanup --dry-run

# Actually perform cleanup
python -m services.ingestion-service.utils.watchlist_manager cleanup --days-inactive 180
```

## Querying Active Symbols

### Get Active Symbols

```python
from database.watchlist_sync import get_active_symbols
from shared.database import DatabaseManager

with DatabaseManager() as db:
    active_symbols = get_active_symbols(db)
    print(f"Active symbols: {active_symbols}")
```

### SQL Query

```sql
-- Get all active symbols
SELECT symbol_id, symbol_name, base_asset, quote_asset
FROM symbols
WHERE is_active = TRUE
ORDER BY symbol_name;
```

### Get OHLCV for Active Symbols Only

```sql
-- Get latest OHLCV for active symbols
SELECT 
    s.symbol_name,
    oc.timestamp,
    oc.open, oc.high, oc.low, oc.close,
    oc.volume
FROM ohlcv_candles oc
INNER JOIN symbols s ON oc.symbol_id = s.symbol_id
WHERE s.is_active = TRUE
ORDER BY oc.timestamp DESC;
```

## Example Queries

See `database/example_queries.py` for complete examples:
- Get active symbols
- Get OHLCV for active symbols
- Get inactive symbols with removal dates
- Get reactivated symbols
- Get market data for active symbols
- Get symbol statistics

## Repository Functions Updated

The following repository functions now filter by `is_active = TRUE`:
- `get_qualified_symbols()`: Only returns active symbols
- `get_or_create_symbol_record()`: Automatically reactivates inactive symbols if they're being used

## Best Practices

1. **Run daily sync** after ingestion completes
2. **Always use dry_run=True** first when running monthly cleanup
3. **Query with `is_active = TRUE`** when displaying data to users
4. **Preserve historical data** - never hard-delete unless cleanup is explicitly run
5. **Monitor inactive symbols** - check `removed_at` dates to understand symbol churn

## Cron Jobs

### Daily Sync (recommended after ingestion)

```cron
# Run daily at 2 AM
0 2 * * * cd /path/to/project && python -m services.ingestion-service.utils.watchlist_manager sync
```

### Monthly Cleanup (first day of month)

```cron
# Run monthly on 1st at 3 AM (with dry-run first to review)
0 3 1 * * cd /path/to/project && python -m services.ingestion-service.utils.watchlist_manager cleanup --days-inactive 180
```

## Idempotency

All functions are **idempotent**:
- `sync_watchlist()`: Safe to call multiple times with the same watchlist
- `cleanup_old_inactive_symbols()`: Safe to call multiple times (won't delete already-deleted symbols)

## Safety Features

1. **Soft-delete by default**: Symbols are marked inactive, not deleted
2. **Dry-run mode**: Preview cleanup before actual deletion
3. **Foreign key constraints**: Database ensures data integrity
4. **Transaction safety**: All operations use database transactions
5. **Logging**: All operations are logged for audit trail

