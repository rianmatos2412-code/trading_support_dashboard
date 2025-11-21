"""
Swing Engine - Detects swing highs and swing lows
"""
import sys
import os
import asyncio
import json
import signal
from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.logger import setup_logger
from shared.config import SWING_LOOKBACK_PERIODS
from shared.redis_client import publish_event, get_redis

logger = setup_logger(__name__)

# Global shutdown event
shutdown_event = asyncio.Event()

# Candle data structure
class CandleData:
    """Simple data structure for candle data"""
    def __init__(self, timestamp: datetime, open: float, high: float, low: float, close: float, volume: float):
        self.timestamp = timestamp
        self.open = Decimal(str(open))
        self.high = Decimal(str(high))
        self.low = Decimal(str(low))
        self.close = Decimal(str(close))
        self.volume = Decimal(str(volume))


def get_symbol_id(db: Session, symbol: str) -> Optional[int]:
    """Get symbol_id for given symbol string"""
    try:
        result = db.execute(
            text("SELECT symbol_id FROM symbols WHERE symbol_name = :symbol LIMIT 1"),
            {"symbol": symbol}
        ).scalar()
        return result
    except Exception as e:
        logger.error(f"Error getting symbol_id for {symbol}: {e}")
        return None


def get_timeframe_id(db: Session, timeframe: str) -> Optional[int]:
    """Get timeframe_id for given timeframe string"""
    try:
        result = db.execute(
            text("SELECT timeframe_id FROM timeframe WHERE tf_name = :tf LIMIT 1"),
            {"tf": timeframe}
        ).scalar()
        return result
    except Exception as e:
        logger.error(f"Error getting timeframe_id for {timeframe}: {e}")
        return None


class SwingEngine:
    """Engine for detecting swing highs and swing lows"""
    
    def __init__(self, lookback_periods: int = SWING_LOOKBACK_PERIODS):
        self.lookback_periods = lookback_periods
    
    def detect_swing_high(
        self, 
        candles: List[CandleData], 
        index: int
    ) -> Optional[Tuple[int, Decimal]]:
        """
        Detect swing high at index
        A swing high is when the high is higher than N periods on both sides
        """
        if index < self.lookback_periods or index >= len(candles) - self.lookback_periods:
            return None
        
        current_high = candles[index].high
        
        # Check left side
        for i in range(index - self.lookback_periods, index):
            if candles[i].high >= current_high:
                return None
        
        # Check right side
        for i in range(index + 1, index + self.lookback_periods + 1):
            if candles[i].high >= current_high:
                return None
        
        return (index, current_high)
    
    def detect_swing_low(
        self, 
        candles: List[CandleData], 
        index: int
    ) -> Optional[Tuple[int, Decimal]]:
        """
        Detect swing low at index
        A swing low is when the low is lower than N periods on both sides
        """
        if index < self.lookback_periods or index >= len(candles) - self.lookback_periods:
            return None
        
        current_low = candles[index].low
        
        # Check left side
        for i in range(index - self.lookback_periods, index):
            if candles[i].low <= current_low:
                return None
        
        # Check right side
        for i in range(index + 1, index + self.lookback_periods + 1):
            if candles[i].low <= current_low:
                return None
        
        return (index, current_low)
    
    def find_swing_points(self, candles: List[CandleData]) -> Tuple[List[Tuple[int, Decimal]], List[Tuple[int, Decimal]]]:
        """Find all swing highs and lows in the candle series"""
        swing_highs = []
        swing_lows = []
        
        # Start from lookback_periods and end before the last lookback_periods
        start_idx = self.lookback_periods
        end_idx = len(candles) - self.lookback_periods
        
        for i in range(start_idx, end_idx):
            swing_high = self.detect_swing_high(candles, i)
            if swing_high:
                swing_highs.append(swing_high)
            
            swing_low = self.detect_swing_low(candles, i)
            if swing_low:
                swing_lows.append(swing_low)
        
        return swing_highs, swing_lows
    
    def save_swing_points(
        self, 
        db: Session, 
        symbol_id: int,
        timeframe_id: int,
        candles: List[CandleData],
        swing_highs: List[Tuple[int, Decimal]],
        swing_lows: List[Tuple[int, Decimal]]
    ) -> List[dict]:
        """Save swing points to database using raw SQL with symbol_id and timeframe_id
        Returns list of newly inserted swing points (only new ones, not existing)
        """
        newly_inserted = []
        try:
            # Prepare insert statement with ON CONFLICT DO NOTHING and RETURNING to get new IDs
            stmt = text("""
                INSERT INTO swing_points 
                (symbol_id, timeframe_id, timestamp, price, type, strength)
                VALUES (:symbol_id, :timeframe_id, :timestamp, :price, :type, :strength)
                ON CONFLICT (symbol_id, timeframe_id, timestamp, type) 
                DO NOTHING
                RETURNING id, timestamp, price, type
            """)
            
            # Save swing highs and track newly inserted ones
            for idx, price in swing_highs:
                candle = candles[idx]
                result = db.execute(stmt, {
                    "symbol_id": symbol_id,
                    "timeframe_id": timeframe_id,
                    "timestamp": candle.timestamp,
                    "price": float(price),
                    "type": "swing_high",
                    "strength": self.lookback_periods
                })
                row = result.fetchone()
                if row:  # Only if it was actually inserted (not a conflict)
                    newly_inserted.append({
                        "id": row[0],
                        "timestamp": row[1],
                        "price": float(row[2]),
                        "type": "high"  # Convert swing_high to high for frontend
                    })
            
            # Save swing lows and track newly inserted ones
            for idx, price in swing_lows:
                candle = candles[idx]
                result = db.execute(stmt, {
                    "symbol_id": symbol_id,
                    "timeframe_id": timeframe_id,
                    "timestamp": candle.timestamp,
                    "price": float(price),
                    "type": "swing_low",
                    "strength": self.lookback_periods
                })
                row = result.fetchone()
                if row:  # Only if it was actually inserted (not a conflict)
                    newly_inserted.append({
                        "id": row[0],
                        "timestamp": row[1],
                        "price": float(row[2]),
                        "type": "low"  # Convert swing_low to low for frontend
                    })
            
            db.commit()
            logger.info(f"Saved {len(swing_highs)} swing highs and {len(swing_lows)} swing lows, {len(newly_inserted)} were new (symbol_id={symbol_id}, timeframe_id={timeframe_id})")
            return newly_inserted
        except Exception as e:
            logger.error(f"Error saving swing points: {e}")
            db.rollback()
            raise
    
    def process_candles(self, symbol: str, timeframe: str, candles: List[CandleData], symbol_id: int, timeframe_id: int):
        """Process candles and detect swing points"""
        if len(candles) < self.lookback_periods * 2 + 1:
            logger.warning(f"Not enough candles for swing detection: {len(candles)} (need at least {self.lookback_periods * 2 + 1})")
            return
        
        swing_highs, swing_lows = self.find_swing_points(candles)
        
        if swing_highs or swing_lows:
            db = SessionLocal()
            try:
                # Save swing points and get newly inserted ones
                newly_inserted = self.save_swing_points(db, symbol_id, timeframe_id, candles, swing_highs, swing_lows)
                
                # Publish individual events for each newly inserted swing point
                for swing_point in newly_inserted:
                    publish_event("swing_point_new", {
                        "id": swing_point["id"],
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "type": swing_point["type"],  # "high" or "low"
                        "price": swing_point["price"],
                        "timestamp": swing_point["timestamp"].isoformat() if hasattr(swing_point["timestamp"], 'isoformat') else str(swing_point["timestamp"])
                    })
                    logger.debug(f"Published new swing point: {symbol} {timeframe} {swing_point['type']} at {swing_point['price']}")
                
                # Also publish summary event for backward compatibility
                latest_high = swing_highs[-1] if swing_highs else None
                latest_low = swing_lows[-1] if swing_lows else None
                publish_event("swing_detected", {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "swing_high": float(latest_high[1]) if latest_high else None,
                    "swing_low": float(latest_low[1]) if latest_low else None,
                    "swing_high_count": len(swing_highs),
                    "swing_low_count": len(swing_lows),
                    "new_swing_points": len(newly_inserted)
                })
            finally:
                db.close()
        else:
            logger.debug(f"No swing points detected for {symbol} {timeframe}")


def fetch_candles(db: Session, symbol: str, timeframe: str, limit: int = 400) -> List[CandleData]:
    """Fetch candles from database using raw SQL with proper joins"""
    try:
        query = text("""
            SELECT 
                oc.timestamp,
                oc.open,
                oc.high,
                oc.low,
                oc.close,
                oc.volume
            FROM ohlcv_candles oc
            INNER JOIN symbols s ON oc.symbol_id = s.symbol_id
            INNER JOIN timeframe t ON oc.timeframe_id = t.timeframe_id
            WHERE s.symbol_name = :symbol
            AND t.tf_name = :timeframe
            ORDER BY oc.timestamp DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"symbol": symbol, "timeframe": timeframe, "limit": limit})
        rows = result.fetchall()
        
        # Convert to CandleData objects and reverse to get oldest first
        candles = []
        for row in rows:
            candles.append(CandleData(
                timestamp=row[0],
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5])
            ))
        
        candles.reverse()  # Oldest first for swing detection
        return candles
    except Exception as e:
        logger.error(f"Error fetching candles for {symbol} {timeframe}: {e}")
        return []


def process_swing_detection(symbol: str, timeframe: str):
    """Process swing detection for a symbol and timeframe"""
    db = SessionLocal()
    try:
        # Get symbol_id and timeframe_id
        symbol_id = get_symbol_id(db, symbol)
        timeframe_id = get_timeframe_id(db, timeframe)
        
        if not symbol_id:
            logger.warning(f"Symbol {symbol} not found in database")
            return
        
        if not timeframe_id:
            logger.warning(f"Timeframe {timeframe} not found in database")
            return
        
        # Fetch 400 candles
        candles = fetch_candles(db, symbol, timeframe, limit=400)
        
        if len(candles) < SWING_LOOKBACK_PERIODS * 2 + 1:
            logger.warning(f"Not enough candles for {symbol} {timeframe}: {len(candles)} (need at least {SWING_LOOKBACK_PERIODS * 2 + 1})")
            return
        
        engine = SwingEngine()
        engine.process_candles(symbol, timeframe, candles, symbol_id, timeframe_id)
        
    except Exception as e:
        logger.error(f"Error in swing detection for {symbol} {timeframe}: {e}", exc_info=True)
    finally:
        db.close()


def get_all_symbols_and_timeframes(db: Session) -> List[Tuple[str, str]]:
    """Get all symbol/timeframe combinations from database"""
    try:
        query = text("""
            SELECT DISTINCT 
                s.symbol_name,
                t.tf_name
            FROM ohlcv_candles oc
            INNER JOIN symbols s ON oc.symbol_id = s.symbol_id
            INNER JOIN timeframe t ON oc.timeframe_id = t.timeframe_id
            ORDER BY s.symbol_name, t.tf_name
        """)
        
        result = db.execute(query)
        rows = result.fetchall()
        
        combinations = [(row[0], row[1]) for row in rows]
        logger.info(f"Found {len(combinations)} symbol/timeframe combinations in database")
        return combinations
    except Exception as e:
        logger.error(f"Error getting symbol/timeframe combinations: {e}")
        return []


def process_all_swing_detections():
    """Process swing detection for all symbol/timeframe combinations"""
    db = SessionLocal()
    try:
        combinations = get_all_symbols_and_timeframes(db)
        
        if not combinations:
            logger.warning("No symbol/timeframe combinations found in database")
            return
        
        total = len(combinations)
        processed = 0
        errors = 0
        
        logger.info(f"Starting batch swing detection for {total} symbol/timeframe combinations")
        
        for symbol, timeframe in combinations:
            # Check shutdown event before processing each combination
            if shutdown_event.is_set():
                logger.info(f"Shutdown requested. Processed {processed}/{total} combinations before stopping.")
                break
            
            try:
                process_swing_detection(symbol, timeframe)
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"Progress: {processed}/{total} combinations processed")
            except Exception as e:
                errors += 1
                logger.error(f"Error processing {symbol} {timeframe}: {e}")
        
        logger.info(f"Batch swing detection completed: {processed} processed, {errors} errors out of {total} total")
        
    except Exception as e:
        logger.error(f"Error in batch swing detection: {e}", exc_info=True)
    finally:
        db.close()


def handle_candle_inserted_event(data: dict):
    """Handle candle_inserted event from Redis"""
    try:
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        
        if not symbol or not timeframe:
            logger.warning(f"Invalid candle_inserted event: missing symbol or timeframe")
            return
        
        logger.info(f"Received candle_inserted event for {symbol} {timeframe}")
        
        # Process swing detection
        process_swing_detection(symbol, timeframe)
        
    except Exception as e:
        logger.error(f"Error handling candle_inserted event: {e}", exc_info=True)


async def listen_for_candle_events():
    """Listen for candle_inserted events from Redis"""
    redis_client = get_redis()
    if not redis_client:
        logger.error("Redis not available, cannot listen for events")
        return
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe("candle_inserted")
    
    logger.info("Swing engine listening for candle_inserted events...")
    
    try:
        while not shutdown_event.is_set():
            # Use asyncio.to_thread for blocking Redis call
            try:
                message = await asyncio.wait_for(
                    asyncio.to_thread(
                        pubsub.get_message,
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    ),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                # Check shutdown event periodically
                continue
            
            if message and message.get("type") == "message":
                try:
                    data = json.loads(message["data"])
                    handle_candle_inserted_event(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing Redis message: {e}")
                except Exception as e:
                    logger.error(f"Error processing candle_inserted event: {e}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping event listener")
    except Exception as e:
        logger.error(f"Error in event listener: {e}", exc_info=True)
    finally:
        logger.info("Closing Redis pubsub connection...")
        try:
            pubsub.close()
        except Exception as e:
            logger.error(f"Error closing pubsub: {e}")
        logger.info("Redis pubsub connection closed")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        signal_name = signal.Signals(signum).name
        logger.info(f"Shutdown signal received: {signal_name} ({signum})")
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main_event_loop():
    """Main event loop for swing engine with graceful shutdown"""
    setup_signal_handlers()
    
    if not init_db():
        logger.error("Database initialization failed")
        return
    
    try:
        # First, process all existing symbol/timeframe combinations
        logger.info("Initializing: Processing swing points for all existing symbol/timeframe combinations...")
        try:
            # Check shutdown event periodically during batch processing
            if not shutdown_event.is_set():
                process_all_swing_detections()
            else:
                logger.info("Shutdown requested before initial processing completed")
                return
            
            if shutdown_event.is_set():
                logger.info("Shutdown requested after initial processing")
                return
                
            logger.info("Initial processing completed. Starting event listener...")
        except Exception as e:
            logger.error(f"Error during initial processing: {e}", exc_info=True)
            if shutdown_event.is_set():
                logger.info("Shutdown requested, skipping event listener")
                return
            logger.info("Continuing with event listener despite initial processing error...")
        
        # Then start listening for new candle events
        await listen_for_candle_events()
        
    except Exception as e:
        logger.error(f"Error in main event loop: {e}", exc_info=True)
    finally:
        logger.info("Swing engine shutdown complete")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Swing Point Detection Engine")
    parser.add_argument("--symbol", type=str, help="Symbol to process (e.g., BTCUSDT)")
    parser.add_argument("--timeframe", type=str, help="Timeframe to process (e.g., 1h)")
    parser.add_argument("--all", action="store_true", help="Process all symbol/timeframe combinations")
    parser.add_argument("--listen", action="store_true", help="Listen for candle_inserted events (default mode)")
    
    args = parser.parse_args()
    
    if args.all:
        # Process all symbol/timeframe combinations
        if not init_db():
            logger.error("Database initialization failed")
        else:
            process_all_swing_detections()
    elif args.symbol and args.timeframe:
        # Process specific symbol/timeframe
        if not init_db():
            logger.error("Database initialization failed")
        else:
            process_swing_detection(args.symbol, args.timeframe)
    else:
        # Default: listen for events
        logger.info("Starting swing engine in event listening mode...")
        asyncio.run(main_event_loop())

