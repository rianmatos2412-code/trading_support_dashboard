-- Migration: Add soft-delete columns to symbols table
-- Created: 2025-01-XX
-- Description: Adds is_active and removed_at columns for soft-delete/hysteresis pattern

-- ============================================================================
-- SYMBOLS SOFT-DELETE COLUMNS
-- ============================================================================

-- Add is_active column (default True for existing rows)
ALTER TABLE symbols 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Add removed_at column (nullable, set when symbol becomes inactive)
ALTER TABLE symbols 
ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ NULL;

-- Create index for active symbols lookup (most common query)
CREATE INDEX IF NOT EXISTS idx_symbols_is_active ON symbols(is_active) WHERE is_active = TRUE;

-- Create index for cleanup queries (symbols removed before a certain date)
CREATE INDEX IF NOT EXISTS idx_symbols_removed_at ON symbols(removed_at) WHERE removed_at IS NOT NULL;

-- Update existing symbols to be active (safety measure)
UPDATE symbols SET is_active = TRUE, removed_at = NULL WHERE is_active IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN symbols.is_active IS 'Whether the symbol is currently in the active watchlist. False means it was removed but historical data is preserved.';
COMMENT ON COLUMN symbols.removed_at IS 'Timestamp when the symbol was removed from the watchlist. NULL if currently active.';

