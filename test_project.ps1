# Trading Support Project Health Check Script
# Run this script to verify your project is working

Write-Host "=== Testing Trading Support Project ===" -ForegroundColor Cyan
Write-Host ""

# Check if docker-compose is available
Write-Host "1. Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version
    Write-Host "   ✅ Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker Compose not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check if services are running
Write-Host ""
Write-Host "2. Checking service status..." -ForegroundColor Yellow
try {
    $services = docker-compose ps --services 2>$null
    if ($services) {
        $running = docker-compose ps --format json | ConvertFrom-Json | Where-Object { $_.State -eq "running" }
        Write-Host "   ✅ Services found: $($services.Count)" -ForegroundColor Green
        Write-Host "   ✅ Running services: $($running.Count)" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  No services found. Run 'docker-compose up -d' first." -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Could not check services. Make sure docker-compose.yml exists." -ForegroundColor Yellow
}

# Test API health
Write-Host ""
Write-Host "3. Testing API health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ API is healthy" -ForegroundColor Green
    } else {
        Write-Host "   ❌ API returned status: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ API is not responding. Is the service running?" -ForegroundColor Red
    Write-Host "      Run: docker-compose up -d api-service" -ForegroundColor Yellow
}

# Test database connection
Write-Host ""
Write-Host "4. Testing database..." -ForegroundColor Yellow
try {
    $dbCheck = docker-compose exec -T postgres psql -U trading_user -d trading_db -c "SELECT COUNT(*) FROM ohlcv_candles;" 2>$null
    if ($dbCheck -match "\d+") {
        $count = [regex]::Match($dbCheck, "\d+").Value
        Write-Host "   ✅ Database is accessible" -ForegroundColor Green
        Write-Host "   📊 Candles in database: $count" -ForegroundColor Cyan
    } else {
        Write-Host "   ⚠️  Could not query database. It may still be initializing." -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Database is not accessible" -ForegroundColor Red
    Write-Host "      Run: docker-compose up -d postgres" -ForegroundColor Yellow
}

# Test Redis
Write-Host ""
Write-Host "5. Testing Redis..." -ForegroundColor Yellow
try {
    $redisCheck = docker-compose exec -T redis redis-cli ping 2>$null
    if ($redisCheck -match "PONG") {
        Write-Host "   ✅ Redis is working" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Redis is not responding" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Redis is not accessible" -ForegroundColor Red
    Write-Host "      Run: docker-compose up -d redis" -ForegroundColor Yellow
}

# Check project files
Write-Host ""
Write-Host "6. Checking project structure..." -ForegroundColor Yellow
$requiredFiles = @(
    "docker-compose.yml",
    "database/init.sql",
    "shared/database.py",
    "services/api-service/main.py",
    "services/ingestion-service/main.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "   ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $file (missing)" -ForegroundColor Red
        $missingFiles += $file
    }
}

if ($missingFiles.Count -eq 0) {
    Write-Host "   ✅ All required files present" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. If services aren't running: docker-compose up -d" -ForegroundColor White
Write-Host "  2. View logs: docker-compose logs -f" -ForegroundColor White
Write-Host "  3. Check API docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  4. See CHECK_PROJECT.md for detailed testing guide" -ForegroundColor White

