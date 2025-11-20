"""
Ingestion Service - Main entry point
Orchestrates ingestion from Binance and CoinGecko APIs
"""
import sys
import os
import asyncio
from datetime import datetime
from sqlalchemy import text
import structlog

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import init_db, DatabaseManager
from shared.redis_client import publish_event
import logging

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout,
    force=True
)
# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Import from modules
from config.settings import (
    DEFAULT_SYMBOLS, DEFAULT_TIMEFRAME, MARKET_DATA_LIMIT
)
from services.binance_service import BinanceIngestionService
from services.coingecko_service import CoinGeckoIngestionService
from services.websocket_service import BinanceWebSocketService
from database.repository import get_qualified_symbols, get_ingestion_timeframes


async def hourly_market_data_update():
    """Background task to update market data every hour with metrics"""
    logger.info("hourly_market_data_update_started")
    while True:
        try:            
            await asyncio.sleep(3600)  # Wait 1 hour
            
            start_time = datetime.now()
            
            # Get all symbols from database that have market data
            with DatabaseManager() as db:
                result = db.execute(
                    text("""
                        SELECT DISTINCT s.symbol_name
                        FROM symbols s
                        INNER JOIN market_data md ON s.symbol_id = md.symbol_id
                        ORDER BY s.symbol_name
                    """)
                ).fetchall()
                symbols = [row[0] for row in result]
            
            if symbols:
                logger.info("hourly_market_data_update_starting", symbol_count=len(symbols))
                # Create service instances for this update
                async with BinanceIngestionService() as binance_service:
                    async with CoinGeckoIngestionService() as coingecko_service:
                        await coingecko_service.update_market_data_for_symbols(
                            symbols, binance_service=binance_service
                        )
                
                # Calculate metrics
                duration = (datetime.now() - start_time).total_seconds()
                symbols_per_second = len(symbols) / duration if duration > 0 else 0
                
                logger.info(
                    "hourly_market_data_update_completed",
                    symbol_count=len(symbols),
                    duration_seconds=duration,
                    symbols_per_second=symbols_per_second
                )
            else:
                logger.warning("hourly_market_data_update_no_symbols")

        except asyncio.CancelledError:
            logger.info("hourly_market_data_update_cancelled")
            break
        except Exception as e:
            logger.error(
                "hourly_market_data_update_error",
                error=str(e),
                exc_info=True
            )
            await asyncio.sleep(60)  # Wait 1 minute before retrying


async def main():
    """Main ingestion loop"""
    if not init_db():
        logger.error("database_initialization_failed")
        return
    
    # Ingest CoinGecko market metrics first, filtered to Binance perpetual contracts
    async with BinanceIngestionService() as binance_service:
        async with CoinGeckoIngestionService() as coingecko_service:
            await coingecko_service.ingest_top_market_metrics(
                limit=MARKET_DATA_LIMIT, binance_service=binance_service
            )
            logger.info("coingecko_market_metrics_ingestion_completed")
    
    # Start hourly market data update task (runs independently)
    update_task = asyncio.create_task(hourly_market_data_update())
    logger.info("hourly_market_data_update_task_started")
    
    try:
        # Get qualified symbols and timeframes from database
        with DatabaseManager() as db:
            timeframes = get_ingestion_timeframes(db)
            symbols = get_qualified_symbols(db)
            if not symbols:
                logger.warning("no_qualified_symbols_using_defaults")
                symbols = DEFAULT_SYMBOLS
        
        logger.info(
            "websocket_ingestion_starting",
            symbol_count=len(symbols),
            timeframe_count=len(timeframes),
            timeframes=timeframes
        )
        
        # Start WebSocket service for real-time OHLCV data
        # This replaces the REST polling loop
        async with BinanceWebSocketService() as ws_service:
            # Start periodic metrics logging task
            async def log_metrics_periodically():
                while True:
                    await asyncio.sleep(300)  # Log every 5 minutes
                    metrics = ws_service.get_metrics()
                    messages_per_sec = (
                        metrics['messages_received'] / 300 
                        if metrics['messages_received'] > 0 else 0
                    )
                    logger.info(
                        "websocket_metrics",
                        messages_received=metrics['messages_received'],
                        messages_per_second=messages_per_sec,
                        parse_errors=metrics['parse_errors'],
                        reconnect_count=metrics['reconnect_count'],
                        is_connected=metrics['is_connected']
                    )
            
            metrics_task = asyncio.create_task(log_metrics_periodically())
            
            try:
                # Start WebSocket service (runs indefinitely with reconnection)
                await ws_service.start(symbols, timeframes)
            finally:
                metrics_task.cancel()
                try:
                    await metrics_task
                except asyncio.CancelledError:
                    pass
    finally:
        # Cancel the hourly update task
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())

