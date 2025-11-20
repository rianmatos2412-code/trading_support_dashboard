"""
Configuration settings for ingestion service with validation
"""
import logging
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Initialize settings with validation
try:
    settings = None  # Will be initialized below
    
    class IngestionSettings(BaseSettings):
        """Pydantic settings for ingestion service with validation
        
        This class loads configuration from environment variables (from .env file or system env)
        and validates them. Field names use snake_case, but map to UPPER_SNAKE_CASE env vars.
        """
        
        # Database
        database_url: str = Field(
            default="postgresql://trading_user:trading_pass@localhost:5432/trading_db",
            alias="DATABASE_URL"
        )
        
        # Binance API
        binance_api_url: str = Field(
            default="",
            alias="BINANCE_API_URL"
        )
        binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
        binance_secret_key: str = Field(default="", alias="BINANCE_SECRET_KEY")
        
        # CoinGecko API
        coingecko_api_url: str = Field(
            default="https://api.coingecko.com/api/v3",
            alias="COINGECKO_API_URL"
        )
        coingecko_min_market_cap: float = Field(
            default=50000000.0,
            alias="COINGECKO_MIN_MARKET_CAP"
        )  # 50M USD
        coingecko_min_volume_24h: float = Field(
            default=50000000.0,
            alias="COINGECKO_MIN_VOLUME_24H"
        )  # 50M USD
        
        # Limits
        market_data_limit: int = Field(default=200, alias="MARKET_DATA_LIMIT")
        symbol_limit: int = Field(default=400, alias="SYMBOL_LIMIT")
        
        # Timeframes
        default_timeframe: str = Field(default="1h", alias="DEFAULT_TIMEFRAME")
        default_symbols: str = Field(default="BTCUSDT,ETHUSDT,SOLUSDT", alias="DEFAULT_SYMBOLS")
        
        # WebSocket Configuration
        ws_batch_size: int = Field(default=50, alias="WS_BATCH_SIZE")
        ws_batch_timeout: float = Field(default=1.0, alias="WS_BATCH_TIMEOUT")
        ws_max_reconnect_delay: int = Field(default=60, alias="WS_MAX_RECONNECT_DELAY")
        ws_ping_interval: int = Field(default=20, alias="WS_PING_INTERVAL")
        ws_ping_timeout: int = Field(default=10, alias="WS_PING_TIMEOUT")
        
        # Database Configuration
        db_batch_size: int = Field(default=100, alias="DB_BATCH_SIZE")
        db_connection_timeout: int = Field(default=10, alias="DB_CONNECTION_TIMEOUT")
        
        # Logging
        log_level: str = Field(default="INFO", alias="LOG_LEVEL")
        
        @field_validator('ws_batch_size')
        @classmethod
        def validate_ws_batch_size(cls, v):
            if v < 1 or v > 1000:
                raise ValueError('ws_batch_size must be between 1 and 1000')
            return v
        
        @field_validator('ws_batch_timeout')
        @classmethod
        def validate_ws_batch_timeout(cls, v):
            if v < 0.1 or v > 60:
                raise ValueError('ws_batch_timeout must be between 0.1 and 60 seconds')
            return v
        
        @field_validator('market_data_limit')
        @classmethod
        def validate_market_data_limit(cls, v):
            if v < 1 or v > 1000:
                raise ValueError('market_data_limit must be between 1 and 1000')
            return v
        
        @field_validator('symbol_limit')
        @classmethod
        def validate_symbol_limit(cls, v):
            if v < 1 or v > 10000:
                raise ValueError('symbol_limit must be between 1 and 10000')
            return v
        
        @field_validator('default_timeframe')
        @classmethod
        def validate_default_timeframe(cls, v):
            supported = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
            if v not in supported:
                raise ValueError(f'default_timeframe must be one of {supported}')
            return v
        
        @field_validator('log_level')
        @classmethod
        def validate_log_level(cls, v):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if v.upper() not in valid_levels:
                raise ValueError(f'log_level must be one of {valid_levels}')
            return v.upper()
        
        model_config = {
            "populate_by_name": True,  # Allow both field name and alias
            "case_sensitive": False,
            "env_file": ".env",
            "env_file_encoding": "utf-8",
            "extra": "ignore"
        }
    
    # Initialize settings with validation
    settings = IngestionSettings()
except Exception as e:
    # Use basic logging if structlog logger not yet available
    temp_logger = logging.getLogger(__name__)
    temp_logger.error(f"Failed to load configuration: {e}", exc_info=True)
    raise

# Backward compatibility - expose settings as module-level variables
BINANCE_API_URL = settings.binance_api_url
COINGECKO_API_URL = settings.coingecko_api_url
COINGECKO_MIN_MARKET_CAP = settings.coingecko_min_market_cap
COINGECKO_MIN_VOLUME_24H = settings.coingecko_min_volume_24h
MARKET_DATA_LIMIT = settings.market_data_limit
SYMBOL_LIMIT = settings.symbol_limit
DEFAULT_TIMEFRAME = settings.default_timeframe
DEFAULT_SYMBOLS = settings.default_symbols.split(",")
WS_BATCH_SIZE = settings.ws_batch_size
WS_BATCH_TIMEOUT = settings.ws_batch_timeout
WS_MAX_RECONNECT_DELAY = settings.ws_max_reconnect_delay
WS_PING_INTERVAL = settings.ws_ping_interval
WS_PING_TIMEOUT = settings.ws_ping_timeout
DB_BATCH_SIZE = settings.db_batch_size

