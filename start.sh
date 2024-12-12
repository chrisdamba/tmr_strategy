#!/bin/bash
set -e

cd gateway && sh bin/run.sh root/conf.yaml &
GATEWAY_PID=$!

# Wait for gateway readiness
echo "Waiting for gateway to become ready..."
until curl -k -f https://localhost:5055/v1/api/tickle >/dev/null 2>&1; do
    sleep 1
done
echo "Gateway is ready."

# Start trading system in background
cd /app
python3 -m trading.trading_system &
TRADING_PID=$!

# Start the web interface
cd webapp
FLASK_RUN_PORT=5056 FLASK_DEBUG=1 flask --app app run -h 0.0.0.0 &
WEBAPP_PID=$!

wait $GATEWAY_PID $TRADING_PID $WEBAPP_PID
