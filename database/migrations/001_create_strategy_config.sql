-- Migration: Create strategy_config table
-- Created: 2025-01-XX
-- Description: Adds strategy_config table to store strategy configuration parameters

-- ============================================================================
-- CONFIGURATION TABLES
-- ============================================================================

-- Strategy configuration table
CREATE TABLE IF NOT EXISTS strategy_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) NOT NULL DEFAULT 'string', -- 'string', 'number', 'json'
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_strategy_config_key ON strategy_config(config_key);

-- Insert default configuration values
INSERT INTO strategy_config (config_key, config_value, config_type, description) VALUES
    ('market_data_limit', '200', 'number', 'Limit for number of market data to ingest'),
    ('symbol_limit', '400', 'number', 'Limit for number of symbols to ingest'),
    ('limit_market_cap', '50000000', 'number', 'Minimum market cap filter (USD)'),
    ('limit_volume_up', '50000000', 'number', 'Minimum 24h volume filter (USD)'),
    ('bullish_fib_level_lower', '0.7', 'number', 'Lower bullish Fibonacci entry level'),
    ('bullish_fib_level_higher', '0.72', 'number', 'Higher bullish Fibonacci entry level'),
    ('bullish_sl_fib_level', '0.9', 'number', 'Bullish stop loss Fibonacci level'),
    ('bearish_fib_level', '0.618', 'number', 'Bearish Fibonacci entry level'),
    ('bearish_sl_fib_level', '0.786', 'number', 'Bearish stop loss Fibonacci level'),
    ('tp1_fib_level', '0.5', 'number', 'Take profit 1 Fibonacci level'),
    ('tp2_fib_level', '0.382', 'number', 'Take profit 2 Fibonacci level'),
    ('tp3_fib_level', '0.236', 'number', 'Take profit 3 Fibonacci level'),
    ('candle_counts_for_swing_high_low', '200', 'number', 'Number of candles for swing high/low detection'),
    ('sensible_window', '2', 'number', 'Sensible window for support/resistance detection'),
    ('swing_window', '7', 'number', 'Swing window for swing point detection'),
    ('swing_high_low_pruning_score', '{"BTCUSDT": 0.015, "ETHUSDT": 0.015, "SOLUSDT": 0.02, "OTHER": 0.03}', 'json', 'Swing high/low pruning scores per symbol')
ON CONFLICT (config_key) DO NOTHING;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON strategy_config TO trading_user;

