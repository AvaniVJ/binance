import os
import time
import logging
from dotenv import load_dotenv
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT

# === Load environment variables ===
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BASE_URL = os.getenv("BINANCE_TESTNET_URL", "https://testnet.binance.vision")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
TRADE_QTY = float(os.getenv("TRADE_QTY", 0.001))

# === Logging ===
logging.basicConfig(
    filename="futures_style_bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# === Binance Client ===
client = Client(API_KEY, API_SECRET)
client.API_URL = f"{BASE_URL}/api"

# === State ===
virtual_balance = {"USDT": 10000.0, "BTC": 1.0}
last_entry_price = None


def check_connection():
    try:
        client.ping()
        print("✅ Connected to Binance Spot Testnet.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        exit()


def get_price(symbol=SYMBOL):
    try:
        price = float(client.get_symbol_ticker(symbol=symbol)["price"])
        return price
    except Exception as e:
        logging.error(f"Price fetch error: {e}")
        return None


def get_price_filters(symbol=SYMBOL):
    """Get price filters for symbol to stay within Binance's allowed range."""
    info = client.get_symbol_info(symbol)
    filters = {f["filterType"]: f for f in info["filters"]}
    return filters


def clamp_price(price, filters):
    """Clamp price to allowed tick and percent ranges."""
    tick_size = float(filters["PRICE_FILTER"]["tickSize"])
    min_price = float(filters["PRICE_FILTER"]["minPrice"])
    max_price = float(filters["PRICE_FILTER"]["maxPrice"])

    # round to nearest tick
    price = round(price / tick_size) * tick_size
    return max(min(price, max_price), min_price)


def place_market_order(side):
    global last_entry_price, virtual_balance

    current_price = get_price()
    if not current_price:
        print("⚠️ Price unavailable.")
        return

    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=TRADE_QTY
        )
        logging.info(f"{side} market order executed: {order}")

        if side == SIDE_BUY:
            last_entry_price = current_price
            print(f"📈 LONG opened at {current_price}")
        else:
            if last_entry_price:
                pnl = (current_price - last_entry_price) * TRADE_QTY
                virtual_balance["USDT"] += pnl
                print(f"📉 SHORT closed at {current_price} | PnL: {pnl:.2f} USDT")
                last_entry_price = None
        print(f"✅ {side} {TRADE_QTY} {SYMBOL} at {current_price}")
    except Exception as e:
        print(f"❌ Market order failed: {e}")
        logging.error(f"Market order failed: {e}")


def place_limit_order(side):
    """Place a limit order safely within Binance constraints."""
    current_price = get_price()
    filters = get_price_filters()

    print(f"📊 Current {SYMBOL} price: {current_price}")
    user_price = float(input("Enter limit price: "))

    valid_price = clamp_price(user_price, filters)
    if valid_price != user_price:
        print(f"⚠️ Adjusted to valid tick: {valid_price}")

    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=side,
            type=ORDER_TYPE_LIMIT,
            quantity=TRADE_QTY,
            price=f"{valid_price:.2f}",
            timeInForce="GTC"
        )
        logging.info(f"{side} limit order placed: {order}")
        print(f"✅ Limit {side} {TRADE_QTY} {SYMBOL} at {valid_price}")
    except Exception as e:
        print(f"❌ Limit order failed: {e}")
        logging.error(f"Limit order failed: {e}")


def auto_strategy():
    global last_entry_price, virtual_balance
    start_price = get_price()
    if not start_price:
        print("⚠️ Price unavailable.")
        return

    print(f"🎯 Starting strategy at {start_price}")
    while True:
        try:
            time.sleep(5)
            current = get_price()
            if not current:
                continue

            change = ((current - start_price) / start_price) * 100
            print(f"💹 {SYMBOL} = {current:.2f} | Δ {change:.3f}% | Balance: {virtual_balance['USDT']:.2f} USDT")

            if change <= -0.2 and not last_entry_price:
                print("📉 Price dropped! Going LONG.")
                place_market_order(SIDE_BUY)
                last_entry_price = current

            elif change >= 0.2 and last_entry_price:
                print("📈 Price up! Closing LONG.")
                place_market_order(SIDE_SELL)
                pnl = (current - last_entry_price) * TRADE_QTY
                virtual_balance["USDT"] += pnl
                print(f"💰 Realized PnL: {pnl:.2f} | Balance: {virtual_balance['USDT']:.2f}")
                last_entry_price = None

        except KeyboardInterrupt:
            print("\n🛑 Strategy stopped by user.")
            break


def main():
    check_connection()
    print(f"💰 Virtual Balance: {virtual_balance['USDT']} USDT | {virtual_balance['BTC']} BTC\n")

    while True:
        print("\n🎯 Actions:")
        print("1️⃣ Market Buy (LONG)")
        print("2️⃣ Market Sell (CLOSE SHORT)")
        print("3️⃣ Limit Buy")
        print("4️⃣ Limit Sell")
        print("5️⃣ Auto Strategy")
        print("6️⃣ Exit")

        choice = input("\nSelect action: ").strip()

        if choice == "1":
            place_market_order(SIDE_BUY)
        elif choice == "2":
            place_market_order(SIDE_SELL)
        elif choice == "3":
            place_limit_order(SIDE_BUY)
        elif choice == "4":
            place_limit_order(SIDE_SELL)
        elif choice == "5":
            auto_strategy()
        elif choice == "6":
            print("🛑 Exiting bot. Goodbye!")
            break
        else:
            print("❓ Invalid choice.")


if __name__ == "__main__":
    main()
