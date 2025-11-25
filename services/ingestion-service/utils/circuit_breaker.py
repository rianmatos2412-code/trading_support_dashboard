"""Circuit breaker pattern for API resilience"""
import asyncio
import time
from typing import Callable, Any, Optional
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class AsyncCircuitBreaker:
    """Async circuit breaker pattern for API resilience"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time >= self.recovery_timeout):
                logger.info("circuit_breaker_half_open", function=func.__name__)
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            # All functions passed to this circuit breaker should be async
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == CircuitState.HALF_OPEN:
                logger.info("circuit_breaker_closed", function=func.__name__)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result
        
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                logger.warning(
                    "circuit_breaker_opened",
                    function=func.__name__,
                    failure_count=self.failure_count
                )
                self.state = CircuitState.OPEN
            
            raise

