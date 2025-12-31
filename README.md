# 📈 Binance Algorithmic Execution Engine

A robust, server-side algorithmic trading bot designed to bridge **TradingView** technical analysis strategies with **Binance Futures** execution.

Deployed on **AWS EC2**, this system operates 24/7, listening for webhook signals to execute trades with millisecond precision, enforcing strict risk management protocols and dynamic position sizing.

---

## 🚀 Key Features

* **24/7 Automated Availability:** Hosted on an AWS EC2 (Ubuntu Linux) instance, ensuring 99.9% uptime.
* **Webhook-Based Architecture:** Eliminates the need for constant polling by using a passive Flask listener, reducing API rate limit risks.
* **Dynamic Risk Management:** Automatically calculates position size based on a configurable risk percentage (e.g., 10% of equity) per trade.
* **Precision Execution:** Handles Binance's specific "Step Size" and "Precision" filters to prevent `Invalid Quantity` errors.
* **Security First:** API credentials are isolated in configuration files and excluded from version control via `.gitignore`.

---

## 🏗️ System Architecture

1.  **Signal Generation (The Brain):** A proprietary Pine Script strategy (Trend-Following/reversal logic) runs on TradingView servers.
2.  **Transmission:** Signals are sent via JSON payloads over HTTP POST requests when entry conditions are met.
3.  **Reception (The Listener):** A Python Flask application running on AWS Port 80 intercepts the payload.
4.  **Processing & Execution:**
    * The bot queries the realtime wallet balance.
    * Calculates the exact contract quantity based on current price and risk parameters.
    * Submits `Market Entry`, `Take Profit`, and `Stop Loss` orders to Binance Futures API simultaneously.

---

## 🔧 Technical Challenges & Solutions

During the development and deployment phase, several critical engineering challenges were addressed:

### 1. Network & Port Restrictions
* **Challenge:** TradingView webhooks strictly require communication over **Port 80 (HTTP)** or **443 (HTTPS)**. Default Flask apps run on Port 5000/9000.
* **Solution:** Configured AWS Security Groups (Firewall) to allow inbound traffic on Port 80 and bound the Flask application to `host='0.0.0.0', port=80` with sudo privileges, bypassing the need for third-party tunneling services like Ngrok for production stability.

### 2. Persistence & Process Management
* **Challenge:** SSH sessions terminate when the local machine disconnects, killing the bot process.
* **Solution:** Implemented **GNU Screen** / Linux background process management (`detached sessions`) to ensure the Python script continues running indefinitely on the server, independent of the developer's active session.

### 3. Precision & Rounding Errors
* **Challenge:** Binance rejects orders if the quantity precision doesn't match the asset's specific `stepSize` (e.g., buying 0.0015 BTC when the step is 0.001).
* **Solution:** Developed a wrapper function `calculate_dynamic_quantity()` that fetches `exchange_info` dynamically and rounds down the calculated quantity to the nearest valid increment using modular arithmetic.

---

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Framework:** Flask (Micro-framework for Webhooks)
* **Cloud Infrastructure:** Amazon Web Services (AWS EC2)
* **OS:** Ubuntu Linux
* **Financial API:** `python-binance` (Async wrapper)
* **Version Control:** Git & GitHub

---

## 🔒 Security Note

This repository contains the **execution logic and architecture**.
* **Strategy Logic:** Proprietary Pine Script strategies are not included.
* **Credentials:** `config.py` containing API keys is excluded via `.gitignore` for security. A template is provided in `config_template.py`.

---

## ⚠️ Disclaimer

This software is for educational and portfolio demonstration purposes. Algorithmic trading involves significant financial risk.


## ⚙️ Deployment Notes (Linux Permissions & Production Setup)
Binding to Privileged Ports (Port 80)

On Linux systems, binding to ports below 1024 (such as Port 80) is restricted to privileged processes.

Instead of running the bot as root, the following capability is explicitly granted to the Python binary:

sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.12


This allows the Flask application to bind securely to Port 80 while preserving best security practices.

Verification:

getcap /usr/bin/python3.12

Background Execution & Process Persistence

To ensure uninterrupted operation after SSH disconnections, the bot is executed inside a detached GNU Screen session:

screen -S borsa
python3 main.py



This guarantees:

No dependency on the developer’s local machine

Continuous 24/7 execution

Safe reattachment for monitoring and logs

AWS Firewall Configuration (Security Groups)

Inbound rules configured on AWS EC2 Security Group:

22 / TCP – SSH access

80 / TCP – TradingView Webhook listener

Outbound traffic is unrestricted to allow Binance API communication.

Webhook Health Verification

Incoming webhook traffic can be confirmed via server logs.
External GET requests to / correctly return 404, indicating:

Server is reachable

Flask is running

Only /webhook POST requests are accepted by design

## ✅ Production Status

Webhook reception: Active

Binance Futures execution: Verified

Hedge Mode: Enabled

Dynamic risk sizing: Operational

Server uptime: 24/7 AWS-backed
