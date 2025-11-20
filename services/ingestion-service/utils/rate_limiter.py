"""Rate limiting utilities for API calls"""
from aiolimiter import AsyncLimiter
import structlog

logger = structlog.get_logger(__name__)

# Binance rate limits (per minute)
# Weight limits: 2400 per minute for futures API
# Conservative limits to avoid hitting rate limits
BINANCE_RATE_LIMIT = AsyncLimiter(max_rate=10, time_period=1)  # 10 requests per second
BINANCE_BURST_LIMIT = AsyncLimiter(max_rate=100, time_period=60)  # 100 requests per minute

# CoinGecko rate limits
# Free tier: 10-50 calls/minute
# Pro tier: higher limits
COINGECKO_RATE_LIMIT = AsyncLimiter(max_rate=1, time_period=1)  # 1 request per second (conservative)
COINGECKO_MINUTE_LIMIT = AsyncLimiter(max_rate=30, time_period=60)  # 30 requests per minute

