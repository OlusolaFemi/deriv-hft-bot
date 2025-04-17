# High-Frequency Trading Bot for Deriv Synthetic Indices
import json
import time

try:
    import websocket
except ImportError:
    websocket = None

# List of synthetic indices to trade
symbols = ["R_10", "R_25", "R_50", "R_75", "R_100"]

# API authentication and app ID (replace API_TOKEN with your own token)
API_TOKEN = "mJKyypWPsYatp6N"  # Replace with your Deriv API token
APP_ID = "1089"  # 1089 is a default Deriv app_id for testing; use your own app_id for live trading

# Trading parameters
STAKE = 2       # USD stake per trade
COOLDOWN = 5    # seconds cooldown per symbol between trades

# Data structures to store recent ticks and last trade times
last_ticks = {symbol: [] for symbol in symbols}
last_trade_time = {symbol: 0 for symbol in symbols}

def on_open(ws):
    """Called when WebSocket connection is opened."""
    print("WebSocket connection opened.")
    # Authenticate with API token
    auth_request = {"authorize": mJKyypWPsYatp6N}
    ws.send(json.dumps(auth_request))

def on_message(ws, message):
    """Called when a new message is received from WebSocket."""
    data = json.loads(message)
    # If an error is returned by the API
    if data.get("error"):
        error_msg = data["error"].get("message", "Unknown error")
        print(f"Error: {error_msg}")
        # If authorization failed, close the connection
        if data["error"].get("code") == "AuthorizationRequired":
            ws.close()
        return

    msg_type = data.get("msg_type")
    if msg_type == "authorize":
        # Successfully authorized; subscribe to tick streams for all symbols
        print("Authorization successful.")
        for symbol in symbols:
            sub_request = {"ticks": symbol, "subscribe": 1}
            ws.send(json.dumps(sub_request))
            print(f"Subscribed to tick stream for {symbol}.")
    elif msg_type == "tick":
        # Tick data received
        tick = data.get("tick", {})
        symbol = tick.get("symbol")
        quote = tick.get("quote")
        if symbol and quote is not None:
            # Store the tick price
            prices = last_ticks[symbol]
            prices.append(quote)
            if len(prices) > 3:
                prices.pop(0)  # keep only last 3 ticks
            # If we have 3 recent ticks, evaluate momentum
            if len(prices) == 3:
                # Check if prices are strictly increasing (upward momentum)
                if prices[0] < prices[1] < prices[2]:
                    if time.time() - last_trade_time[symbol] >= COOLDOWN:
                        # Place a CALL (rise) trade
                        buy_request = {
                            "buy": 1,
                            "price": STAKE,
                            "parameters": {
                                "amount": STAKE,
                                "basis": "stake",
                                "contract_type": "CALL",  # Rise contract
                                "currency": "USD",
                                "duration": 1,
                                "duration_unit": "t",
                                "symbol": symbol
                            }
                        }
                        ws.send(json.dumps(buy_request))
                        last_trade_time[symbol] = time.time()
                        print(f"Signal: ↑↑↑ {symbol} - Buying CALL at price {quote}")
                # Check if prices are strictly decreasing (downward momentum)
                elif prices[0] > prices[1] > prices[2]:
                    if time.time() - last_trade_time[symbol] >= COOLDOWN:
                        # Place a PUT (fall) trade
                        buy_request = {
                            "buy": 1,
                            "price": STAKE,
                            "parameters": {
                                "amount": STAKE,
                                "basis": "stake",
                                "contract_type": "PUT",   # Fall contract
                                "currency": "USD",
                                "duration": 1,
                                "duration_unit": "t",
                                "symbol": symbol
                            }
                        }
                        ws.send(json.dumps(buy_request))
                        last_trade_time[symbol] = time.time()
                        print(f"Signal: ↓↓↓ {symbol} - Buying PUT at price {quote}")
    elif msg_type == "buy":
        # Confirmation of a completed trade
        buy = data.get("buy", {})
        contract_id = buy.get("contract_id")
        buy_price = buy.get("buy_price")
        payout = buy.get("payout")
        if contract_id:
            print(f"Trade executed on {buy.get('symbol')}: contract_id={contract_id}, buy_price={buy_price}, payout={payout}")
    # (Other message types like 'proposal', 'balance', etc., can be handled if needed)

def on_error(ws, error):
    """Called when a WebSocket error occurs."""
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Called when the WebSocket connection is closed."""
    print("WebSocket connection closed.")

if not websocket:
    print("Please install the 'websocket-client' library to run this script.")
else:
    # Connect to Deriv's WebSocket API
    ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}"
    ws_app = websocket.WebSocketApp(ws_url,
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
    print("Starting trading bot... (press Ctrl+C to stop)")
    ws_app.run_forever()
