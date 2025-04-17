import asyncio
import websockets
import json
import time
import statistics
from datetime import datetime

DERIV_TOKEN = "***********NnEk"
SYMBOLS = ["R_10", "R_25", "R_50", "R_75", "R_100"]

BUFFER_SIZE = 50
STD_DEV_THRESHOLD = 2
COOLDOWN_SECONDS = 5
DEFAULT_STAKE = 2
REDUCED_STAKE = 1
DAILY_PROFIT_TARGET = 100
DAILY_LOSS_LIMIT = 20

tick_buffers = {symbol: [] for symbol in SYMBOLS}
last_trade_time = {symbol: 0 for symbol in SYMBOLS}
stake_state = {symbol: DEFAULT_STAKE for symbol in SYMBOLS}

daily_profit = 0
daily_loss = 0
current_day = datetime.utcnow().day

async def send(ws, payload):
    await ws.send(json.dumps(payload))

async def reset_daily_limits():
    global daily_profit, daily_loss, current_day
    today = datetime.utcnow().day
    if today != current_day:
        print("⏳ New day detected. Resetting daily counters.")
        current_day = today
        daily_profit = 0
        daily_loss = 0

async def evaluate_and_trade(ws, symbol, price):
    global daily_profit, daily_loss

    # Daily limits check
    if daily_profit >= DAILY_PROFIT_TARGET:
        print("✅ Daily profit target hit. Pausing trades until reset.")
        return
    if daily_loss <= -DAILY_LOSS_LIMIT:
        print("🛑 Daily loss limit hit. Pausing trades until reset.")
        return

    ticks = tick_buffers[symbol]
    if len(ticks) < BUFFER_SIZE:
        return

    mean = statistics.mean(ticks)
    stdev = statistics.stdev(ticks)

    # Check deviation
    if stdev == 0:
        return

    upper = mean + STD_DEV_THRESHOLD * stdev
    lower = mean - STD_DEV_THRESHOLD * stdev

    # Basic swing detection (macro-style)
    recent = ticks[-5:]
    trend_up = all(x < y for x, y in zip(recent, recent[1:]))
    trend_down = all(x > y for x, y in zip(recent, recent[1:]))

    now = time.time()
    if now - last_trade_time[symbol] < COOLDOWN_SECONDS:
        return

    contract_type = None
    if price > upper and trend_down:
        contract_type = "PUT"
    elif price < lower and trend_up:
        contract_type = "CALL"

    if contract_type:
        stake = stake_state[symbol]
        contract = {
            "buy": 1,
            "price": stake,
            "parameters": {
                "amount": stake,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": 1,
                "duration_unit": "t",
                "symbol": symbol
            }
        }
        await send(ws, contract)
        last_trade_time[symbol] = now
        print(f"📈 {symbol}: {contract_type} | Price: {price} | Stake: ${stake}")

async def main():
    uri = "wss://ws.deriv.com/websockets/v3"
    async with websockets.connect(uri) as ws:
        await send(ws, {"authorize": DERIV_TOKEN})
        managers = {}

        while True:
            response = json.loads(await ws.recv())

            if "error" in response:
                print("❌ Error:", response["error"]["message"])
                break

            if response.get("msg_type") == "authorize":
                print("🔑 Authorized. Subscribing to symbols...")
                for symbol in SYMBOLS:
                    await send(ws, {"ticks": symbol, "subscribe": 1})

            elif response.get("msg_type") == "tick":
                tick = response["tick"]
                symbol = tick["symbol"]
                price = float(tick["quote"])
                ticks = tick_buffers[symbol]
                ticks.append(price)
                if len(ticks) > BUFFER_SIZE:
                    ticks.pop(0)
                await reset_daily_limits()
                await evaluate_and_trade(ws, symbol, price)

            elif response.get("msg_type") == "buy":
                contract = response["buy"]
                print(f"🟢 Bought: {contract['contract_type']} | ID: {contract['contract_id']}")

            elif response.get("msg_type") == "proposal_open_contract":
                result = response["proposal_open_contract"]
                symbol = result["underlying"]
                profit = float(result["profit"])

                if profit > 0:
                    print(f"✅ PROFIT ${profit}")
                    daily_profit += profit
                    stake_state[symbol] = DEFAULT_STAKE
                else:
                    print(f"🔻 LOSS ${profit}")
                    daily_loss += profit
                    stake_state[symbol] = REDUCED_STAKE

if __name__ == "__main__":
    print("🚀 Starting Deriv HFT Bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user.")
