"""
Event Listener Service

This module handles listening to Redis events for candle updates.
"""
import json
import asyncio
import structlog
import sys
import os

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.redis_client import get_redis

logger = structlog.get_logger(__name__)


class EventListener:
    """Listens to Redis events and processes candle updates."""
    
    def __init__(self, callback):
        """
        Initialize the event listener.
        
        Args:
            callback: Async function to call when a candle update is received
        """
        self.callback = callback
        self.redis_client = get_redis()
        self.pubsub = None
        self.shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start listening to candle update events."""
        if not self.redis_client:
            logger.error("redis_not_available")
            return
        
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe("candle_update")
        
        logger.info("strategy_engine_listener_started")
        
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Get message with timeout
                    message = self.pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
                    
                    if message and message.get("type") == "message":
                        try:
                            data = json.loads(message["data"])
                            await self.callback(data)
                        except json.JSONDecodeError as e:
                            logger.error("error_parsing_message", error=str(e))
                        except Exception as e:
                            logger.error("error_processing_message", error=str(e))
                    
                except Exception as e:
                    if not self.shutdown_event.is_set():
                        logger.error("error_in_listener_loop", error=str(e))
                        await asyncio.sleep(1)
        finally:
            if self.pubsub:
                self.pubsub.close()
            logger.info("strategy_engine_listener_stopped")
    
    def stop(self):
        """Stop listening to events."""
        self.shutdown_event.set()

