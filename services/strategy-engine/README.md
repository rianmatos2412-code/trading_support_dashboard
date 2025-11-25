# Strategy Engine

A modular and scalable trading strategy engine that combines swing high/low detection, support/resistance levels, Fibonacci calculations, and confluence scoring to generate trading alerts.

## Structure

The strategy engine is organized into the following modules:

### Core Modules (`core/`)
- **`strategy_interface.py`**: Main strategy orchestrator that combines all components
- **`strategy.py`**: High-level strategy wrapper (`RunStrategy` class)
- **`models.py`**: Data models (`FibResult`, `ConfirmedFibResult`)
- **`confluence.py`**: Confluence analysis and confirmation logic

### Configuration (`config/`)
- **`settings.py`**: Configuration management with database-backed values and defaults

### Indicators (`indicators/`)
- **`swing_points.py`**: Swing high/low detection and filtering
- **`support_resistance.py`**: Support/resistance level detection
- **`fibonacci.py`**: Fibonacci level calculations

### Alerts (`alerts/`)
- **`generator.py`**: Alert generation from confirmed Fibonacci levels
- **`database.py`**: Database operations for storing and retrieving alerts

### Data Access (`data/`)
- **`repository.py`**: Repository pattern for accessing candle data from database

### Services (`services/`)
- **`candle_service.py`**: Service for processing candle data
- **`event_listener.py`**: Redis event listener for candle updates

### Entry Point
- **`main.py`**: Main service entry point that initializes and runs the strategy engine

## Key Features

1. **Modular Design**: Each component has a single responsibility
2. **Scalable**: Easy to add new indicators, strategies, or data sources
3. **Reusable**: Components can be used independently
4. **Testable**: Clear separation of concerns makes unit testing easier
5. **Configurable**: Configuration is centralized and database-backed

## Usage

The strategy engine listens to Redis `candle_update` events and automatically executes the strategy when new 4H or 30M candles are detected.

## Migration Notes

The old files (`strategy_interface.py`, `swing_high_low.py`, `support_resistance.py`, `alert_database.py`) are kept at the root level for backward compatibility but are deprecated. New code should use the modular structure.

