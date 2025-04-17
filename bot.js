const WebSocket = require('ws');

const ws = new WebSocket('wss://ws.deriv.com/websockets/v3');

const API_TOKEN = 'h6No2RTmCEWhnkN'; // Replace this with your Deriv token
const SYMBOL = 'R_100';

let prices = [];
let isAuthorized = false;

ws.onopen = () => {
    console.log('Connected to Deriv WebSocket');

    // Step 1: Authorize
    ws.send(JSON.stringify({
        authorize: h6No2RTmCEWhnkN
    }));
};

ws.onmessage = (msg) => {
    const data = JSON.parse(msg.data);

    // Step 2: Handle Authorization
    if (data.msg_type === 'authorize') {
        isAuthorized = true;
        console.log('Authorized!');

        // Step 3: Subscribe to Tick Stream
        ws.send(JSON.stringify({
            ticks: SYMBOL,
            subscribe: 1
        }));
    }

    // Step 4: Handle Tick Data
    if (data.msg_type === 'tick') {
        const tick = data.tick;
        console.log(`Tick: ${tick.quote}`);

        prices.push(tick.quote);
        if (prices.length > 10) prices.shift(); // Keep only the last 10 prices

        const avg = prices.reduce((a, b) => a + b, 0) / prices.length;

        if (tick.quote > avg) {
            console.log('Condition met: price > average. Buying...');
            buyContract(SYMBOL);
        }
    }

    // Step 6: Handle Buy Response
    if (data.msg_type === 'buy') {
        console.log('Contract Purchased:', data.buy);
    }

    if (data.error) {
        console.error('Error:', data.error.message);
    }
};

function buyContract(symbol) {
    const proposal = {
        buy: 1,
        price: 1,
        parameters: {
            amount: 1,
            basis: 'stake',
            contract_type: 'CALL',
            currency: 'USD',
            duration: 1,
            duration_unit: 'm',
            symbol: symbol
        }
    };

    ws.send(JSON.stringify(proposal));
}
