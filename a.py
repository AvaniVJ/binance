import os
import time
import logging
from dotenv import load_dotenv
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET

# === Load environment variables ===
load_dotenv()

# ✅ Your real keys go here in the .env file, not directly in code
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BASE_URL = os.getenv("BINANCE_TESTNET_URL", "https://testnet.binance.vision")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
TRADE_QUANTITY = float(os.getenv("TRADE_QUANTITY", 0.001))

# === Configure logging ===
logging.basicConfig(
    filename="spot_trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# === Initialize client ===
client = Client(API_KEY, API_SECRET)
client.API_URL = f"{BASE_URL}/api"

# === Global variables for tracking ===
profit_usdt = 0.0
last_buy_price = None


def check_connection():
    """Test connection to Binance API."""
    try:
        client.ping()
        logging.info("Connection successful.")
        print("✅ Connected to Binance Testnet.")
    except Exception as e:
        logging.error(f"Connection failed: {e}")
        print("❌ Connection failed. Check keys or network.")


def get_balance(asset="USDT"):
    """Fetch account balance for given asset."""
    try:
        account = client.get_account()
        balances = account["balances"]
        for b in balances:
            if b["asset"] == asset:
                return float(b["free"])
    except Exception as e:
        logging.error(f"Error getting balance: {e}")
    return 0.0


def get_price(symbol=SYMBOL):
    """Fetch current price for symbol."""
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        logging.error(f"Error fetching price: {e}")
        return None


def place_order(side, quantity, symbol=SYMBOL):
    """Place a market order (buy or sell)."""
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        logging.info(f"{side} order executed: {order}")
        print(f"✅ {side} {quantity} {symbol}")
        return order
    except Exception as e:
        logging.error(f"Order failed: {e}")
        print(f"❌ Order failed: {e}")
        return None


def simple_strategy():
    """Buy if price drops >0.1%, sell if rises >0.1%, track profit."""
    global profit_usdt, last_buy_price

    price_start = get_price()
    if not price_start:
        print("⚠️ Price unavailable.")
        return

    print(f"Initial {SYMBOL} price: {price_start}")
    while True:
        try:
            time.sleep(5)
            current = get_price()
            if not current:
                continue

            change = ((current - price_start) / price_start) * 100
            print(f"Price: {current:.2f} | Change: {change:.4f}% | Profit: {profit_usdt:.2f} USDT")

            # Buy logic (price drops)
            if change <= -0.1:
                order = place_order(SIDE_BUY, TRADE_QUANTITY)
                if order:
                    last_buy_price = current
                    logging.info(f"Bought {TRADE_QUANTITY} {SYMBOL} at {current}")
                    price_start = current

            # Sell logic (price rises)
            elif change >= 0.1 and last_buy_price:
                order = place_order(SIDE_SELL, TRADE_QUANTITY)
                if order:
                    trade_profit = (current - last_buy_price) * TRADE_QUANTITY
                    profit_usdt += trade_profit
                    logging.info(f"Sold {TRADE_QUANTITY} {SYMBOL} at {current}, Profit: {trade_profit:.2f} USDT")
                    print(f"💰 Trade profit: {trade_profit:.2f} USDT | Total: {profit_usdt:.2f} USDT")
                    last_buy_price = None
                    price_start = current

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped manually. Session ended safely.")
            logging.info("Bot stopped by user.")
            break


def main():
    check_connection()
    usdt = get_balance("USDT")
    btc = get_balance("BTC")
    print(f"💰 Starting Balance: {usdt} USDT | {btc} BTC\n")
    simple_strategy()


if __name__ == "__main__":
    main()
