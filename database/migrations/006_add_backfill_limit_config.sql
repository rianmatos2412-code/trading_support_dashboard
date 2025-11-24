-- Migration: Add backfill_limit configuration
-- Created: 2025-01-XX
-- Description: Adds backfill_limit configuration to ingestion_config table for controlling the number of candles to fetch during backfill operations

-- ============================================================================
-- BACKFILL LIMIT CONFIGURATION
-- ============================================================================

-- Insert backfill_limit configuration
INSERT INTO ingestion_config (config_key, config_value, config_type, description) VALUES
    ('backfill_limit', '400', 'number', 'Number of recent candles to fetch per symbol/timeframe during backfill operations')
ON CONFLICT (config_key) 
DO UPDATE SET
    config_value = EXCLUDED.config_value,
    config_type = EXCLUDED.config_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- Add comment for documentation
COMMENT ON COLUMN ingestion_config.config_key IS 'Unique configuration key identifier (includes backfill_limit for gap detection)';

