"""
BINANCE API CONFIGURATION
-------------------------
WARNING: This file contains sensitive credentials.
Never commit your actual API keys to a public GitHub repository.
Use 'Environment Variables' or a local '.env' file in production.
"""

# Binance Public API Key
# (Get this from your Binance Futures Dashboard)
API_KEY = "YOUR_BINANCE_API_KEY_HERE"

# Binance Secret API Key
# (Keep this strictly confidential. Do not share!)
API_SECRET = "YOUR_BINANCE_SECRET_KEY_HERE"

# Network Selection
# True  = Binance Testnet (Paper Trading / Simulation)
# False = Binance Mainnet (Real Money Trading)
TESTNET = False