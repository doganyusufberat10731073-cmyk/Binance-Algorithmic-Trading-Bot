from flask import Flask, request
from binance.client import Client
from binance.enums import *
from config import API_KEY, API_SECRET, TESTNET

app = Flask(__name__)

# --- RİSK YÖNETİMİ AYARLARI ---
RISK_PERCENT = 0.10  # Boştaki paranın %10'u
LEVERAGE = 50        # Kaldıraç oranı

# 1. BINANCE BAĞLANTISI
client = Client(API_KEY, API_SECRET)

if TESTNET:
    client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

# 2. GERÇEK BOŞ BAKİYEYİ BULMA (MaxWithdrawAmount)
def get_available_balance():
    """
    Binance'in 'maxWithdrawAmount' verisini çeker.
    Bu, işlemdeki parayı ve limit emirleri HARİÇ tutar.
    Sadece gerçekten kullanabileceğin parayı verir.
    """
    try:
        # futures_account() fonksiyonu daha detaylı bilgi verir
        account_info = client.futures_account()
        for asset in account_info['assets']:
            if asset['asset'] == 'USDT':
                # 'maxWithdrawAmount' en güvenilir veridir
                return float(asset['maxWithdrawAmount'])
    except Exception as e:
        print(f"Bakiye hatası: {e}")
        return 0.0
    return 0.0

# 3. FİYAT ÇEKME
def get_price(symbol):
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        print(f"Fiyat hatası: {e}")
        return 0.0

# 4. %10 RİSKLE MİKTAR HESAPLAMA
def calculate_dynamic_quantity(symbol):
    # A) Sadece BOŞTAKİ parayı çek
    free_balance = get_available_balance()
    
    if free_balance <= 0:
        print("❌ HATA: Kullanılabilir bakiye 0 veya eksi!")
        return 0.0

    # B) Marjin Hesapla: Boştaki paranın %10'u
    margin_to_use = free_balance * RISK_PERCENT
    
    # C) Kaldıraçlı Büyüklük (Notional Value)
    target_notional = margin_to_use * LEVERAGE
    
    # KORUMA: Eğer hesaplanan işlem 5.1 Doların altındaysa, Binance hata verir.
    # Bu durumda işlem büyüklüğünü minimum 6 Dolara sabitleriz ki işlem açılsın.
    if target_notional < 6.0:
        print(f"⚠️ UYARI: Hesaplanan tutar ({target_notional}$) çok düşük. 6$'a tamamlanıyor.")
        target_notional = 6.0

    # D) Fiyatı Çek ve Coin Adedini Bul
    price = get_price(symbol)
    if price == 0: return 0.0
    
    raw_qty = target_notional / price

    # E) Binance Küsürat Ayarı (Step Size)
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] == symbol:
            step_size = float(s['filters'][1]['stepSize'])
            qty = (raw_qty // step_size) * step_size
            
            print(f"💰 KASA: {free_balance}$ | RİSK: %{RISK_PERCENT*100} | İŞLEM BÜYÜKLÜĞÜ: {target_notional}$")
            return round(qty, 3)

    return 0.0

# 5. HEDGE MODU İÇİN AKILLI EMİR
def place_hedge_order(symbol, action, quantity, tp, sl):
    try:
        # Hedge Modu Ayarları
        if action == "LONG":
            side_order = SIDE_BUY
            position_side = "LONG"
            side_close = SIDE_SELL
        elif action == "SHORT":
            side_order = SIDE_SELL
            position_side = "SHORT"
            side_close = SIDE_BUY
        else:
            return

        # A) ANA İŞLEMİ AÇ
        client.futures_create_order(
            symbol=symbol,
            side=side_order,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            positionSide=position_side  # Hedge Modu Kilidi
        )
        print(f"✅ POZİSYON AÇILDI: {symbol} {position_side}")

        # B) TAKE PROFIT (KAR AL)
        client.futures_create_order(
            symbol=symbol,
            side=side_close,
            type=ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=tp,
            closePosition=True,
            positionSide=position_side
        )

        # C) STOP LOSS (ZARAR KES)
        client.futures_create_order(
            symbol=symbol,
            side=side_close,
            type=ORDER_TYPE_STOP_MARKET,
            stopPrice=sl,
            closePosition=True,
            positionSide=position_side
        )
        print(f"🛡️ TP: {tp} / SL: {sl} Eklendi.")

    except Exception as e:
        print(f"🚨 EMİR HATASI: {e}")

# 6. SİNYAL DİNLEYİCİ
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print(f"📩 SİNYAL: {data}")

        symbol = data.get("symbol")
        action = data.get("action")
        tp = float(data.get("tp"))
        sl = float(data.get("sl"))

        qty = calculate_dynamic_quantity(symbol)

        if qty > 0:
            place_hedge_order(symbol, action, qty, tp, sl)
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Yetersiz Bakiye"}

    except Exception as e:
        print(f"WEBHOOK HATASI: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)