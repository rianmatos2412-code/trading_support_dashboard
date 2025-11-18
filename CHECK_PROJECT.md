# How to Check/Test the Trading Support Project

## Step 1: Verify Project Structure

First, let's make sure all files are in place:

```bash
# Check directory structure
ls -la
ls -la services/
ls -la shared/
ls -la database/
```

You should see:
- `docker-compose.yml`
- `database/init.sql`
- `shared/` directory with Python files
- `services/` directory with 10 service folders

## Step 2: Set Up Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env if needed (defaults should work for local testing)
# You can use default values for now
```

## Step 3: Start Services

```bash
# Start all services
docker-compose up -d

# This will start:
# - PostgreSQL/TimescaleDB
# - Redis
# - All 10 microservices
```

## Step 4: Check Service Status

```bash
# Check if all services are running
docker-compose ps

# You should see all services with "Up" status
# If any are not running, check logs (Step 5)
```

Expected output:
```
NAME                STATUS
trading_postgres    Up
trading_redis       Up
trading_ingestion   Up
trading_processing  Up
trading_swing       Up
trading_sr          Up
trading_fib         Up
trading_confluence  Up
trading_risk        Up
trading_storage     Up
trading_api         Up
trading_worker      Up
```

## Step 5: Check Service Logs

```bash
# View all logs
docker-compose logs

# View logs for specific service
docker-compose logs api-service
docker-compose logs ingestion-service
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f api-service
```

**What to look for:**
- ✅ "Database connection established"
- ✅ "Redis connection established"
- ✅ "API service started"
- ❌ Any ERROR messages

## Step 6: Test Database Connection

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U trading_user -d trading_db

# Once connected, run:
\dt                    # List all tables
SELECT * FROM fib_config;  # Check Fibonacci config
\q                     # Exit
```

**Expected:** You should see tables like `ohlcv_candles`, `trading_signals`, etc.

## Step 7: Test API Endpoints

### 7.1 Health Check

```bash
# Test API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy"}
```

### 7.2 Root Endpoint

```bash
curl http://localhost:8000/

# Expected response:
# {"message":"Trading Support API","version":"1.0.0"}
```

### 7.3 View API Documentation

Open in browser: **http://localhost:8000/docs**

This shows the interactive Swagger UI with all endpoints.

### 7.4 Test Signal Endpoints

```bash
# Get all signals (may be empty initially)
curl http://localhost:8000/signals

# Get latest signal for a symbol (may return 404 if no data yet)
curl http://localhost:8000/signals/BTCUSDT/latest

# Get signals summary
curl http://localhost:8000/signals/summary
```

## Step 8: Test Data Ingestion

```bash
# Check ingestion service logs
docker-compose logs -f ingestion-service

# You should see:
# - "Starting ingestion service for symbols: ..."
# - "Fetched X klines for BTCUSDT"
# - "Saved X candles to database"
```

**Wait 1-2 minutes** for data to be ingested, then check:

```bash
# Check if candles are being saved
docker-compose exec postgres psql -U trading_user -d trading_db -c "SELECT COUNT(*) FROM ohlcv_candles;"

# Should show a number > 0 after a few minutes
```

## Step 9: Test Processing Pipeline

After data is ingested, check if processing is working:

```bash
# Check processing service logs
docker-compose logs processing-service

# Look for:
# - "Processed new candle for BTCUSDT"
# - "candle_ready" events
```

## Step 10: Check if Signals Are Generated

```bash
# Check trading signals table
docker-compose exec postgres psql -U trading_user -d trading_db -c "SELECT symbol, market_score, direction, price FROM trading_signals ORDER BY timestamp DESC LIMIT 5;"

# Check swing points
docker-compose exec postgres psql -U trading_user -d trading_db -c "SELECT symbol, type, price FROM swing_points ORDER BY timestamp DESC LIMIT 5;"

# Check S/R levels
docker-compose exec postgres psql -U trading_user -d trading_db -c "SELECT symbol, type, level, strength FROM support_resistance WHERE is_active = true LIMIT 5;"
```

## Step 11: Test API with Real Data

Once signals are generated:

```bash
# Get latest signal (formatted)
curl http://localhost:8000/signals/BTCUSDT/latest | python -m json.tool

# Get candles
curl http://localhost:8000/candles/BTCUSDT?timeframe=1h&limit=10

# Get S/R levels
curl http://localhost:8000/sr-levels/BTCUSDT?timeframe=1h

# Get swings
curl http://localhost:8000/swings/BTCUSDT?timeframe=1h
```

## Step 12: Monitor System Health

```bash
# Check all services are still running
docker-compose ps

# Check resource usage
docker stats

# Check specific service resource usage
docker stats trading_api
```

## Common Issues & Solutions

### Issue 1: Services won't start

```bash
# Check what's wrong
docker-compose logs

# Common causes:
# - Port already in use (5432, 6379, 8000)
# - Database not ready yet
# - Missing environment variables

# Solution: Wait 30 seconds and try again
docker-compose restart
```

### Issue 2: Database connection errors

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U trading_user

# If not ready, wait and check logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Issue 3: No data being ingested

```bash
# Check ingestion logs
docker-compose logs ingestion-service

# Check if Binance API is accessible
curl https://api.binance.com/api/v3/ping

# Should return: {}

# Check network connectivity
docker-compose exec ingestion-service ping -c 3 api.binance.com
```

### Issue 4: API returns 500 errors

```bash
# Check API logs
docker-compose logs api-service

# Check if database is accessible from API service
docker-compose exec api-service python -c "from shared.database import init_db; print(init_db())"
```

### Issue 5: Worker not processing tasks

```bash
# Check worker logs
docker-compose logs worker-service

# Check Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG

# Check if Celery can connect
docker-compose exec worker-service celery -A main inspect active
```

## Quick Health Check Script

Create a simple test script:

```bash
# Create test script
cat > test_project.sh << 'EOF'
#!/bin/bash

echo "=== Testing Trading Support Project ==="

echo "1. Checking services..."
docker-compose ps | grep -c "Up" | xargs -I {} echo "Services running: {}"

echo "2. Testing API health..."
curl -s http://localhost:8000/health | grep -q "healthy" && echo "✅ API is healthy" || echo "❌ API is not responding"

echo "3. Testing database..."
docker-compose exec -T postgres psql -U trading_user -d trading_db -c "SELECT COUNT(*) FROM ohlcv_candles;" | grep -E "[0-9]+" | xargs -I {} echo "Candles in database: {}"

echo "4. Testing Redis..."
docker-compose exec -T redis redis-cli ping | grep -q "PONG" && echo "✅ Redis is working" || echo "❌ Redis is not responding"

echo "=== Test Complete ==="
EOF

chmod +x test_project.sh
./test_project.sh
```

## Expected Timeline

- **0-30 seconds**: Services start up
- **30-60 seconds**: Database initialized, connections established
- **1-2 minutes**: First data ingestion begins
- **2-5 minutes**: First candles saved, processing begins
- **5-10 minutes**: First signals generated (if enough data)

## Next Steps After Verification

1. **Customize Configuration**: Edit `.env` to change symbols, timeframes
2. **Monitor Logs**: Keep `docker-compose logs -f` running
3. **Check API Docs**: Visit http://localhost:8000/docs regularly
4. **Query Database**: Use SQL to analyze signals
5. **Scale Services**: Add more worker instances if needed

## Summary Checklist

- [ ] All services are running (`docker-compose ps`)
- [ ] API responds to health check
- [ ] Database is accessible
- [ ] Redis is working
- [ ] Ingestion service is fetching data
- [ ] Candles are being saved
- [ ] Processing service is detecting new candles
- [ ] Signals are being generated (after 5-10 minutes)
- [ ] API endpoints return data

---

**If all checks pass, your project is working correctly!** 🎉

