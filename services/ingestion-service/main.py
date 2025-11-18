"""
Ingestion Service - Fetches market data from Binance
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.models import OHLCVCandle, MarketData, AssetInfo
from shared.logger import setup_logger
from shared.config import BINANCE_API_URL, DEFAULT_SYMBOLS, DEFAULT_TIMEFRAME
from shared.redis_client import publish_event, cache_get, cache_set

logger = setup_logger(__name__)


class BinanceIngestionService:
    """Service for ingesting data from Binance API"""
    
    def __init__(self):
        self.base_url = BINANCE_API_URL
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_klines(
        self, 
        symbol: str, 
        interval: str = "1h", 
        limit: int = 500
    ) -> List[List]:
        """Fetch OHLCV klines from Binance"""
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Fetched {len(data)} klines for {symbol}")
                    return data
                else:
                    logger.error(f"Failed to fetch klines: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []
    
    async def fetch_ticker_24h(self, symbol: str) -> Optional[Dict]:
        """Fetch 24h ticker data"""
        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {"symbol": symbol}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def fetch_exchange_info(self) -> Optional[Dict]:
        """Fetch exchange information"""
        try:
            url = f"{self.base_url}/api/v3/exchangeInfo"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error fetching exchange info: {e}")
            return None
    
    def parse_klines(self, klines: List[List], symbol: str, timeframe: str) -> List[OHLCVCandle]:
        """Parse klines data into OHLCVCandle objects"""
        candles = []
        for kline in klines:
            try:
                candle = OHLCVCandle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(kline[0] / 1000),
                    open=float(kline[1]),
                    high=float(kline[2]),
                    low=float(kline[3]),
                    close=float(kline[4]),
                    volume=float(kline[5])
                )
                candles.append(candle)
            except Exception as e:
                logger.error(f"Error parsing kline: {e}")
                continue
        return candles
    
    def save_candles(self, db: Session, candles: List[OHLCVCandle]):
        """Save candles to database with conflict handling"""
        try:
            for candle in candles:
                # Use INSERT ... ON CONFLICT DO NOTHING
                stmt = text("""
                    INSERT INTO ohlcv_candles 
                    (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (:symbol, :timeframe, :timestamp, :open, :high, :low, :close, :volume)
                    ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
                """)
                db.execute(stmt, {
                    "symbol": candle.symbol,
                    "timeframe": candle.timeframe,
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume
                })
            db.commit()
            logger.info(f"Saved {len(candles)} candles to database")
        except Exception as e:
            logger.error(f"Error saving candles: {e}")
            db.rollback()
            raise
    
    async def ingest_symbol(self, symbol: str, timeframe: str = DEFAULT_TIMEFRAME):
        """Ingest data for a single symbol"""
        logger.info(f"Starting ingestion for {symbol} ({timeframe})")
        
        # Fetch klines
        klines = await self.fetch_klines(symbol, timeframe, limit=500)
        if not klines:
            logger.warning(f"No klines fetched for {symbol}")
            return
        
        # Parse and save
        candles = self.parse_klines(klines, symbol, timeframe)
        if candles:
            db = SessionLocal()
            try:
                self.save_candles(db, candles)
                # Publish event
                publish_event("candle_update", {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": candles[-1].timestamp.isoformat()
                })
            finally:
                db.close()
        
        # Fetch and save ticker data
        ticker = await self.fetch_ticker_24h(symbol)
        if ticker:
            db = SessionLocal()
            try:
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=float(ticker.get("lastPrice", 0))
                )
                db.merge(market_data)
                db.commit()
            except Exception as e:
                logger.error(f"Error saving market data: {e}")
                db.rollback()
            finally:
                db.close()
    
    async def ingest_all_symbols(self, symbols: List[str], timeframe: str = DEFAULT_TIMEFRAME):
        """Ingest data for multiple symbols"""
        tasks = [self.ingest_symbol(symbol, timeframe) for symbol in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    """Main ingestion loop"""
    if not init_db():
        logger.error("Database initialization failed")
        return
    
    symbols = DEFAULT_SYMBOLS
    timeframe = DEFAULT_TIMEFRAME
    
    logger.info(f"Starting ingestion service for symbols: {symbols}")
    
    async with BinanceIngestionService() as service:
        while True:
            try:
                await service.ingest_all_symbols(symbols, timeframe)
                logger.info("Ingestion cycle completed")
                await asyncio.sleep(60)  # Wait 1 minute before next cycle
            except KeyboardInterrupt:
                logger.info("Ingestion service stopped")
                break
            except Exception as e:
                logger.error(f"Error in ingestion loop: {e}")
                await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())

