"""
Processing Service - Processes OHLCV data and triggers analysis
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.models import OHLCVCandle
from shared.logger import setup_logger
from shared.config import DEFAULT_TIMEFRAME, DEFAULT_SYMBOLS
from shared.redis_client import get_redis, publish_event

logger = setup_logger(__name__)


class ProcessingService:
    """Service for processing OHLCV data"""
    
    def __init__(self):
        self.redis = get_redis()
    
    def get_latest_candle(self, db: Session, symbol: str, timeframe: str) -> Optional[OHLCVCandle]:
        """Get the latest candle for a symbol"""
        try:
            return db.query(OHLCVCandle).filter(
                and_(
                    OHLCVCandle.symbol == symbol,
                    OHLCVCandle.timeframe == timeframe
                )
            ).order_by(desc(OHLCVCandle.timestamp)).first()
        except Exception as e:
            logger.error(f"Error getting latest candle: {e}")
            return None
    
    def get_recent_candles(
        self, 
        db: Session, 
        symbol: str, 
        timeframe: str, 
        limit: int = 100
    ) -> List[OHLCVCandle]:
        """Get recent candles for analysis"""
        try:
            return db.query(OHLCVCandle).filter(
                and_(
                    OHLCVCandle.symbol == symbol,
                    OHLCVCandle.timeframe == timeframe
                )
            ).order_by(desc(OHLCVCandle.timestamp)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent candles: {e}")
            return []
    
    def check_new_candle(self, symbol: str, timeframe: str) -> bool:
        """Check if there's a new candle that needs processing"""
        db = SessionLocal()
        try:
            latest_candle = self.get_latest_candle(db, symbol, timeframe)
            if not latest_candle:
                return False
            
            # Check if we've already processed this candle
            cache_key = f"processed:{symbol}:{timeframe}:{latest_candle.timestamp.isoformat()}"
            if self.redis and self.redis.get(cache_key):
                return False
            
            # Check if candle is recent (within last 5 minutes)
            time_diff = datetime.now(latest_candle.timestamp.tzinfo) - latest_candle.timestamp
            if time_diff < timedelta(minutes=5):
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking new candle: {e}")
            return False
        finally:
            db.close()
    
    def mark_candle_processed(self, symbol: str, timeframe: str, timestamp: datetime):
        """Mark a candle as processed"""
        if self.redis:
            cache_key = f"processed:{symbol}:{timeframe}:{timestamp.isoformat()}"
            self.redis.setex(cache_key, 3600, "1")  # 1 hour TTL
    
    def process_new_candle(self, symbol: str, timeframe: str):
        """Process a new candle and trigger analysis"""
        db = SessionLocal()
        try:
            latest_candle = self.get_latest_candle(db, symbol, timeframe)
            if not latest_candle:
                return
            
            # Mark as processed
            self.mark_candle_processed(symbol, timeframe, latest_candle.timestamp)
            
            # Get recent candles for analysis
            candles = self.get_recent_candles(db, symbol, timeframe, limit=200)
            candles.reverse()  # Oldest first
            
            if len(candles) < 50:
                logger.warning(f"Not enough candles for {symbol}, have {len(candles)}")
                return
            
            # Publish event to trigger analysis
            publish_event("candle_ready", {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": latest_candle.timestamp.isoformat(),
                "price": float(latest_candle.close),
                "candle_count": len(candles)
            })
            
            logger.info(f"Processed new candle for {symbol} at {latest_candle.timestamp}")
            
        except Exception as e:
            logger.error(f"Error processing candle: {e}")
        finally:
            db.close()
    
    async def process_loop(self):
        """Main processing loop"""
        symbols = DEFAULT_SYMBOLS
        timeframe = DEFAULT_TIMEFRAME
        
        logger.info("Starting processing service")
        
        while True:
            try:
                for symbol in symbols:
                    if self.check_new_candle(symbol, timeframe):
                        self.process_new_candle(symbol, timeframe)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logger.info("Processing service stopped")
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(10)


async def main():
    """Main entry point"""
    if not init_db():
        logger.error("Database initialization failed")
        return
    
    service = ProcessingService()
    await service.process_loop()


if __name__ == "__main__":
    asyncio.run(main())

