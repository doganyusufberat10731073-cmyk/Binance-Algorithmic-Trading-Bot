from flask import Flask, request
from binance.client import Client
from binance.enums import *
from config import API_KEY, API_SECRET, TESTNET

app = Flask(__name__)

# --- CONFIGURATION & RISK MANAGEMENT ---
# Risk 10% of the total wallet balance per trade
RISK_PERCENT = 0.10
# Leverage set to 50x for calculation purposes
LEVERAGE = 50

# 1. BINANCE API CONNECTION
client = Client(API_KEY, API_SECRET)
if TESTNET:
    # Redirect to Binance Testnet for safe testing
    client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

# 2. GET WALLET BALANCE
def get_usdt_balance():
    """
    Retrieves the current USDT balance from the Binance Futures wallet.
    Returns:
        float: The available USDT balance. Returns 0.0 if an error occurs.
    """
    try:
        balance_info = client.futures_account_balance()
        for b in balance_info:
            if b['asset'] == 'USDT':
                return float(b['balance'])
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return 0.0
    return 0.0

# 3. GET CURRENT PRICE
def get_price(symbol):
    """
    Fetches the current market price for the given symbol.
    """
    ticker = client.futures_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

# 4. DYNAMIC QUANTITY CALCULATION (Risk Management)
def calculate_dynamic_quantity(symbol):
    """
    Calculates the position size based on the wallet balance, risk percentage, and leverage.
    Automatically adjusts the quantity according to Binance's 'Step Size' filter.
    """
    # A) Fetch current wallet balance
    balance = get_usdt_balance()
    if balance <= 0:
        print("Insufficient or Zero Balance!")
        return 0.0

    # B) Calculate Target Notional Value
    # Formula: (Balance * Risk %) * Leverage
    margin_amount = balance * RISK_PERCENT
    target_notional = margin_amount * LEVERAGE
    
    # C) Get current price to calculate raw quantity
    price = get_price(symbol)
    
    # D) Adjust for Binance 'Step Size' (Precision Filter)
    # This prevents 'Invalid Quantity' errors from the exchange
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] == symbol:
            step_size = float(s['filters'][1]['stepSize']) 
            raw_qty = target_notional / price
            # Round down to the nearest step size
            qty = (raw_qty // step_size) * step_size
            
            print(f"Wallet: {balance}$ | Margin Used: {margin_amount}$ ({RISK_PERCENT*100}%) | Notional Value: {target_notional}$")
            return round(qty, 3)
            
    return 0.001 # Default fallback to prevent crash

# 5. SMART ORDER EXECUTION (Entry + TP/SL)
def place_order_smart(symbol, side, quantity, tp_price, sl_price):
    """
    Places a Market Order and immediately attaches Take Profit and Stop Loss orders.
    Args:
        symbol (str): Trading pair (e.g., 'BTCUSDT')
        side (str): 'LONG' or 'SHORT'
        quantity (float): Calculated quantity
        tp_price (float): Take Profit price from TradingView
        sl_price (float): Stop Loss price from TradingView
    """
    try:
        # Determine Binance side enum
        if side == "LONG":
            main_side = "BUY"
            exit_side = "SELL"
        else:
            main_side = "SELL"
            exit_side = "BUY"

        # 1. PLACE MAIN MARKET ORDER
        client.futures_create_order(
            symbol=symbol,
            side=main_side,
            type="MARKET", 
            quantity=quantity
        )
        print(f"POSITION OPENED! ({main_side}) - Qty: {quantity}")

        # 2. PLACE TAKE PROFIT ORDER
        client.futures_create_order(
            symbol=symbol, side=exit_side, type="TAKE_PROFIT_MARKET",
            stopPrice=tp_price, closePosition=True
        )
        
        # 3. PLACE STOP LOSS ORDER
        client.futures_create_order(
            symbol=symbol, side=exit_side, type="STOP_MARKET",
            stopPrice=sl_price, closePosition=True
        )
        print(f"TP ({tp_price}) and SL ({sl_price}) ATTACHED!")

    except Exception as e:
        print(f"ORDER EXECUTION ERROR: {e}")

# 6. WEBHOOK LISTENER
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Main endpoint to receive JSON alerts from TradingView.
    Triggers the dynamic calculation and order placement logic.
    """
    try:
        data = request.json
        print(f"SIGNAL RECEIVED: {data}")
        
        symbol = data.get("symbol")
        action = data.get("action") # 'LONG' or 'SHORT'
        tv_tp = float(data.get("tp"))
        tv_sl = float(data.get("sl"))
        
        # Calculate dynamic quantity based on real-time balance
        quantity = calculate_dynamic_quantity(symbol)
        
        if quantity > 0:
            place_order_smart(symbol, action, quantity, tv_tp, tv_sl)
            return {"status": "ok"}
        else:
            print("Quantity calculation failed. No trade executed.")
            return {"status": "error", "message": "Insufficient Balance"}
            
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Run on Port 80 for production access via AWS
    app.run(host='0.0.0.0', port=80)