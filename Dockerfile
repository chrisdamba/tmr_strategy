FROM debian:bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y openjdk-17-jre-headless unzip curl procps vim net-tools python3 python3-pip python3.11-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Download IB Client Portal Gateway
RUN mkdir gateway && cd gateway && \
    curl -O https://download2.interactivebrokers.com/portal/clientportal.gw.zip && \
    unzip clientportal.gw.zip && rm clientportal.gw.zip

# Copy configuration files
COPY conf.yaml gateway/root/conf.yaml
COPY config.json /app/config.json
COPY requirements.txt /app/requirements.txt
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy trading and webapp code
COPY trading /app/trading
COPY webapp /app/webapp

# Create logs directory
RUN mkdir /app/logs

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5055 5056

CMD ["/app/start.sh"]
