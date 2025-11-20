"""Type definitions for ingestion service"""
from typing import TypedDict
from datetime import datetime


class KlineData(TypedDict):
    """Type definition for parsed kline data from WebSocket"""
    symbol: str
    timeframe: str
    open_ts: int  # Open timestamp in milliseconds
    close_ts: int  # Close timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool
    timestamp: datetime

