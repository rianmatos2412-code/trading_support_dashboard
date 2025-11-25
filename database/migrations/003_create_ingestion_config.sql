-- Migration: Create ingestion_config table
-- Created: 2025-01-XX
-- Description: Adds ingestion_config table to store ingestion service configuration parameters

-- ============================================================================
-- INGESTION CONFIGURATION TABLE
-- ============================================================================

-- Ingestion configuration table
CREATE TABLE IF NOT EXISTS ingestion_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) NOT NULL DEFAULT 'number', -- 'string', 'number', 'json'
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_config_key ON ingestion_config(config_key);

-- Insert default ingestion configuration values
INSERT INTO ingestion_config (config_key, config_value, config_type, description) VALUES
    ('limit_volume_up', '50000000', 'number', 'Minimum 24h volume filter for Binance perpetuals (USD)'),
    ('limit_market_cap', '50000000', 'number', 'Minimum market cap filter from CoinGecko (USD)'),
    ('coingecko_limit', '250', 'number', 'Number of top coins to fetch from CoinGecko by market cap')
ON CONFLICT (config_key) DO NOTHING;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ingestion_config TO trading_user;

-- Add comment for documentation
COMMENT ON TABLE ingestion_config IS 'Configuration table for ingestion service settings';
COMMENT ON COLUMN ingestion_config.config_key IS 'Unique configuration key identifier';
COMMENT ON COLUMN ingestion_config.config_value IS 'Configuration value as text (will be parsed based on config_type)';
COMMENT ON COLUMN ingestion_config.config_type IS 'Type of configuration value: string, number, or json';
COMMENT ON COLUMN ingestion_config.description IS 'Human-readable description of the configuration parameter';
COMMENT ON COLUMN ingestion_config.updated_at IS 'Timestamp when the configuration was last updated';
COMMENT ON COLUMN ingestion_config.updated_by IS 'User or service that last updated the configuration';

