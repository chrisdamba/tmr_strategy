# Interactive Brokers Algorithmic Trading System

## Overview

This project implements an automated trading system using Interactive Brokers' Client Portal Gateway API. The system combines technical analysis-based stock screening with automated trade execution, all packaged in a containerized environment for reliable deployment.

The trading strategy implements a trend mean reversion approach, looking for pullback opportunities in trending stocks while managing risk through position sizing and portfolio-level constraints.

## System Architecture

### Core Components

The system consists of three main services running in a single container:

1. **IB Client Portal Gateway**: A Java-based service provided by Interactive Brokers that handles authentication and API access. This gateway translates our local REST API calls into IB's proprietary protocol.

2. **Trading System**: A Python-based service that implements our trading strategy. It continuously monitors the market, generates trading signals, and executes trades when conditions are met.

3. **Web Interface**: A Flask-based dashboard that provides visibility into the system's operation, current positions, and trading history.


## Features

- **Client Portal Gateway Integration**: Authenticate locally and route all IBKR Web API calls through a secured local endpoint.
- **Strategy & Logic**:
  - **Stock Screener** for generating buy/sell signals.
  - **Position Manager** and **Risk Manager** to maintain position limits and risk parameters.
- **Observability & Reliability**:
  - Structured logging to both console and file.
  - Exponential backoff on errors in the trading loop.
  - Health checks and readiness checks ensure services start in the correct order.
  - Metrics logging for signals, orders, and cycle durations.
  
- **Configuration & Extensibility**:
  - Parameters (tickers, intervals, account ID) defined via environment variables for easy environment switching.
  - `config.json` and environment variables provide flexibility in adjusting strategy parameters.
  - `docker-compose.yml` defines the runtime environment.


### Directory Structure

```
project_root/
├── docker-compose.yml    # Container orchestration and configuration
├── Dockerfile            # Container build instructions
├── start.sh              # Container startup script
├── conf.yaml             # Gateway configuration
├── config.json           # Trading strategy parameters
├── requirements.txt      # Python dependencies
├── webapp/               # Web interface directory
│   ├── app.py            # Flask application
│   └── templates/        # HTML templates
└── trading/              # Trading system directory
    ├── __init__.py
    ├── trading_system.py    # Main trading logic
    ├── risk_manager.py      # Risk management component
    ├── position_manager.py  # Position management component
    └── stock_screener.py    # Strategy implementation
```

- `Dockerfile`: Builds the Docker image with the Gateway, trading system, and web UI.
- `docker-compose.yml`: Orchestrates container startup and environment variables.
- `start.sh`: Entry script that starts the Gateway, waits for readiness, then starts the trading system and web app.
- `conf.yaml`: Configuration for the IBKR Client Portal Gateway.
- `config.json`: Base strategy parameters.
- `requirements.txt`: Python dependencies for both trading and webapp.
- `webapp/`: Contains the Flask application code.
- `trading/`: Contains the trading strategy components (screener, risk manager, etc.).


## Installation and Setup

### Prerequisites

- Docker and Docker Compose
- Interactive Brokers account
- Paper trading account recommended for initial testing

### Environment Configuration

Create a `.env` file in the project root with your specific configuration:

```env
IBKR_ACCOUNT_ID=Your_Account_ID
TRADING_CHECK_INTERVAL=60
MAX_POSITIONS=10
ALLOCATION_PER_TRADE=1000
MAX_DRAWDOWN=0.2
MAX_POSITION_SIZE=0.1
TICKERS=AAPL,MSFT,GOOGL,AMZN,META
PROFIT_THRESHOLD=2.0
MIN_PRICE=5.0
```

### Building and Running

1. Build the Docker container:
```bash
docker compose build
```

2. Start the system:
```bash
docker compose up -d
```

   This will:
   - Launch the IB Client Portal Gateway on `https://localhost:5055`.
   - Launch the trading system and web app after the gateway is ready.

2. **Authenticate with IBKR**:
   - Open `https://localhost:5055` in your browser.
   - Log in with your IBKR credentials and complete any required 2FA steps.
   - Once authenticated, the gateway session is established locally.

3. **Access the Web UI**:
   - Open `http://localhost:5056` in your browser.
   - The UI might display simple dashboards or instructions on using the system.
   
## Trading Strategy

The system implements a trend mean reversion strategy with the following key components:

### Signal Generation
- Identifies stocks in strong uptrends using price channels
- Looks for pullback opportunities within the trend
- Validates signals using volume and volatility filters

### Risk Management
- Position-level sizing based on account equity and volatility
- Portfolio-level exposure limits
- Maximum drawdown constraints
- Stop-loss and profit-taking rules

### Execution Logic
- Uses limit orders for entries to control execution costs
- Implements smart order routing through IB's systems
- Handles partial fills and order modifications
- Includes retry logic for failed operations

## Configuration

### Trading Parameters

The system's behavior can be configured through environment variables and the config.json file:

- Environment variables control operational parameters (position limits, allocation sizes)
- config.json contains strategy-specific parameters (technical indicators, thresholds)

### Gateway Configuration

The conf.yaml file controls the IB Gateway's behavior:
- SSL settings
- Network access controls
- Connection parameters
- API endpoint configuration

## Monitoring and Maintenance

### Health Checks

The system implements multiple levels of health monitoring:

1. Docker-level health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-k", "--fail", "https://localhost:5055/v1/api/tickle"]
  interval: 10s
  timeout: 5s
  retries: 5
```

2. Application-level monitoring through the web interface

3. Logging to both console and files:
```
/app/logs/trading.log
/app/logs/gateway.log
```

## How It Works

- **Client Portal Gateway**: Provides a local HTTPS endpoint (`https://localhost:5055`) that proxies requests to IBKR’s Web API. After logging in via the browser, all subsequent API calls from within the container are authenticated.
- **Trading System**:
  - Periodically fetches market data (via the Gateway).
  - Runs the `StockScreener` to identify buy/sell signals.
  - Checks portfolio and orders against `RiskManager` and `PositionManager` logic.
  - Places orders if conditions are met.
  - Logs cycle metrics and errors.
- **Web UI**: Provides a simple frontend to check accounts, look up contracts, view and cancel orders, and possibly visualize signals or performance metrics.

## Logging & Metrics

The system maintains detailed logs of all operations:
- Trading signals generated
- Orders placed and their execution
- Risk checks and position management
- System health and error conditions
- Logs are stored in `/app/logs/trading.log` within the container.
- Console logs are also visible with `docker-compose logs`.
- Metrics (signals, orders, cycle duration) are printed at the end of each trading cycle in the logs. Integrate with external monitoring (e.g., Prometheus, ELK stack) for advanced observability.

## Error Handling & Recovery

- If the trading cycle encounters errors (e.g., network issues, unexpected API responses), the system logs the error and performs exponential backoff (waiting longer after each failed retry).
- The gateway readiness is checked before starting the trading logic to ensure no premature requests fail due to the gateway being unready.


## Development and Extension

### Adding New Strategies

To implement a new trading strategy:

1. Create a new strategy class in the trading directory
2. Implement the required methods:
   - `generate_signals()`
   - `validate_signals()`
   - `calculate_position_size()`

3. Update config.json with strategy-specific parameters

### Testing

The system supports multiple testing approaches:

1. Paper trading mode using IB's simulation environment
2. Historical backtesting through the included analysis tools
3. Unit tests for individual components

## Troubleshooting

- **Cannot Access Gateway**: Ensure ports `5055` and `5056` are free and that `docker-compose up` ran without errors.
- **Authentication Fails**: Double-check your IBKR credentials and ensure you’re logging in on the same machine running the gateway.
- **No Data or Orders**: Confirm authentication succeeded. Check logs for errors (`docker-compose logs`).
- **Performance Issues**: Adjust `check_interval` or refine the strategy code for efficiency.

Common issues and their solutions:

1. Authentication failures:
   - Verify IB credentials
   - Check Gateway logs for connection issues
   - Ensure port 5055 is accessible

2. Order execution issues:
   - Verify account permissions
   - Check available buying power
   - Review order logs for rejection reasons

3. Strategy performance issues:
   - Monitor execution latency
   - Review signal generation logs
   - Check market data quality


## Production Considerations

- **Security**: 
  - Ensure `conf.yaml` and certificates are properly configured for production.
  - Consider installing and using valid SSL certificates for the gateway.
  - SSL encryption for all API communications 
  - Environment variable-based secrets management 
  - IP-based access controls in conf.yaml 
  - Container isolation of components
- **Scaling**:
  - The current setup runs all services in one container. For larger environments, consider separate containers for the gateway, trading system, and web UI.
- **Monitoring & CI/CD**:
  - Integrate health checks and metrics into a CI/CD pipeline.
  - Use Docker Compose or Kubernetes for more complex deployments.

## Support and Resources

- [Interactive Brokers API Documentation](https://www.interactivebrokers.com/api/doc.html)
- [Client Portal Gateway Guide](https://www.interactivebrokers.com/en/software/cpwebapi/cpwebapi.htm)
- Project Issues: Submit via GitHub issue tracker
- Community Support: Available through project discussions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Pull requests, bug reports, and feature suggestions are welcome. Please ensure code is linted and tested before submitting a PR.
