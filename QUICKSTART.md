# Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### 1. Start All Services

```bash
docker-compose up -d
```

### 2. Check Services Status

```bash
docker-compose ps
```

### 3. View API Documentation

Open browser: http://localhost:8000/docs

### 4. Test API

```bash
# Health check
curl http://localhost:8000/health

# Get latest signal
curl http://localhost:8000/signals/BTCUSDT/latest

# Get all signals
curl http://localhost:8000/signals
```

### 5. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api-service
docker-compose logs -f ingestion-service
```

## 📊 Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U trading_user -d trading_db

# Useful queries
SELECT * FROM latest_signals;
SELECT * FROM trading_signals ORDER BY timestamp DESC LIMIT 10;
SELECT symbol, COUNT(*) FROM trading_signals GROUP BY symbol;
```

## 🔧 Common Commands

```bash
# Restart a service
docker-compose restart api-service

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild a service
docker-compose build api-service
docker-compose up -d api-service
```

## 🐛 Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs <service-name>

# Check if dependencies are running
docker-compose ps
```

### Database connection error
```bash
# Wait for database to be ready
docker-compose up -d postgres
sleep 10

# Check database
docker-compose exec postgres pg_isready -U trading_user
```

### Redis connection error
```bash
# Check Redis
docker-compose exec redis redis-cli ping
```

## 📝 Next Steps

1. Configure symbols in `.env`: `DEFAULT_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT`
2. Adjust timeframes: `DEFAULT_TIMEFRAME=1h`
3. Monitor ingestion: `docker-compose logs -f ingestion-service`
4. Check signals: `curl http://localhost:8000/signals/summary`

