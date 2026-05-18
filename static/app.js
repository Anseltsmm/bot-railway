const socket = io({
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 999999,
    reconnectionDelay: 1000
});

// ======================
// CHART
// ======================

const labels = [];
const pnlData = [];

const chart = new Chart(
    document.getElementById('pnlChart'),
    {
        type: 'line',

        data: {
            labels: labels,

            datasets: [{
                label: 'Realtime PNL',
                data: pnlData,
                borderWidth: 3,
                tension: 0.4
            }]
        },

        options: {
            responsive: true,

            plugins: {
                legend: {
                    labels: {
                        color: 'white'
                    }
                }
            },

            scales: {
                x: {
                    ticks: {
                        color: 'white'
                    }
                },

                y: {
                    ticks: {
                        color: 'white'
                    }
                }
            }
        }
    }
);

// ======================
// HELPERS
// ======================

function setText(id, value) {

    const el = document.getElementById(id);

    if (!el) return;

    el.innerText = value;
}

function setTF(id, value) {

    const el = document.getElementById(id);

    if (!el) return;

    el.innerText = value || '-';

    el.classList.remove(
        'green',
        'red',
        'yellow'
    );

    if (value === 'BULLISH') {

        el.classList.add('green');

    } else if (value === 'BEARISH') {

        el.classList.add('red');

    } else {

        el.classList.add('yellow');

    }
}

// ======================
// TRADINGVIEW
// ======================

let currentSymbol = null;

function loadTradingView(symbol) {

    if (currentSymbol === symbol) return;

    currentSymbol = symbol;

    document.getElementById(
        'tradingview_chart'
    ).innerHTML = "";

    new TradingView.widget({

        width: "100%",
        height: 550,

        symbol: "BINANCE:" + symbol,

        interval: "5",

        timezone: "Asia/Jakarta",

        theme: "dark",

        style: "1",

        locale: "en",

        toolbar_bg: "#0f172a",

        enable_publishing: false,

        hide_top_toolbar: false,

        save_image: false,

        container_id: "tradingview_chart"
    });
}

loadTradingView("BTCUSDT");

// ======================
// SOCKET CONNECT
// ======================

socket.on('connect', () => {

    console.log("SOCKET CONNECTED");
});

socket.on('disconnect', () => {

    console.log("SOCKET DISCONNECTED");
});

// ======================
// MAIN UPDATE
// ======================

socket.on('update', function (data) {

    console.log("UPDATE:", data);

    // ======================
    // BASIC
    // ======================

    setText(
        'symbol',
        data.symbol || '-'
    );

    setText(
        'price',
        Number(data.price || 0).toFixed(4)
    );

    setText(
        'balance',
        '$' + Number(data.balance || 0).toFixed(2)
    );

    setText(
        'position',
        data.position || 'NONE'
    );

    setText(
        'entry',
        Number(data.entry || 0).toFixed(4)
    );

    // ======================
    // TP SL TRAILING
    // ======================

    const slPrice =
        parseFloat(data.sl_price ?? 0);

    const tpPrice =
        parseFloat(data.tp_price ?? 0);

    const trail =
        parseFloat(data.trail ?? 0);

    setText(
        'sl',
        slPrice > 0
            ? slPrice.toFixed(4)
            : '-'
    );

    setText(
        'tp',
        tpPrice > 0
            ? tpPrice.toFixed(4)
            : '-'
    );

    setText(
        'trail',
        trail > 0
            ? trail.toFixed(2) + '%'
            : '-'
    );

    // ======================
    // PNL
    // ======================

    const pnl =
        Number(data.pnl || 0);

    setText(
        'pnl',
        pnl.toFixed(4)
    );

    setText(
        'pnl_idr',
        'Rp ' +
        Number(data.pnl_idr || 0)
            .toLocaleString()
    );

    const pnlEl =
        document.getElementById('pnl');

    pnlEl.classList.remove(
        'green',
        'red'
    );

    if (pnl >= 0) {

        pnlEl.classList.add('green');

    } else {

        pnlEl.classList.add('red');
    }

    // ======================
    // RSI
    // ======================

    setText(
        'rsi',
        Number(data.rsi || 0).toFixed(2)
    );

    // ======================
    // TREND
    // ======================

    setText(
        'market_trend',
        data.trend || '-'
    );

    setText(
        'market_structure',
        data.structure || '-'
    );

    // ======================
    // SCORE
    // ======================

    setText(
        'long_score',
        data.long_score || 0
    );

    setText(
        'short_score',
        data.short_score || 0
    );

    // ======================
    // CONFIDENCE
    // ======================

    setText(
        'confidence',
        (data.confidence || 0) + '%'
    );

    // ======================
    // MTF
    // ======================

    setText(
        'bullish_tf',
        data.mtf_bullish || 0
    );

    setText(
        'bearish_tf',
        data.mtf_bearish || 0
    );

    // ======================
    // WINRATE
    // ======================

    setText(
        'trade_count',
        data.trade_count || 0
    );

    setText(
        'winrate',
        (data.winrate || 0) + '%'
    );

    // ======================
    // SIGNAL COLOR
    // ======================

    const signalEl =
        document.getElementById('signal');

    signalEl.innerText =
        data.signal || 'NONE';

    signalEl.classList.remove(
        'signal-long',
        'signal-short',
        'signal-none'
    );

    if (data.signal === 'LONG') {

        signalEl.classList.add(
            'signal-long'
        );

    } else if (
        data.signal === 'SHORT'
    ) {

        signalEl.classList.add(
            'signal-short'
        );

    } else {

        signalEl.classList.add(
            'signal-none'
        );
    }

    // ======================
    // MULTI TF
    // ======================

    if (data.mtf) {

        setTF(
            'tf_1m',
            data.mtf["1m"]
        );

        setTF(
            'tf_5m',
            data.mtf["5m"]
        );

        setTF(
            'tf_15m',
            data.mtf["15m"]
        );

        setTF(
            'tf_1h',
            data.mtf["1h"]
        );

        setTF(
            'tf_2h',
            data.mtf["2h"]
        );

        setTF(
            'tf_4h',
            data.mtf["4h"]
        );

        setTF(
            'tf_1d',
            data.mtf["1d"]
        );

        setTF(
            'tf_1w',
            data.mtf["1w"]
        );
    }

    // ======================
    // PNL CHART
    // ======================

    labels.push(
        new Date()
            .toLocaleTimeString()
    );

    pnlData.push(pnl);

    if (labels.length > 50) {

        labels.shift();
        pnlData.shift();
    }

    chart.update('none');

    // ======================
    // TV CHART
    // ======================

    if (data.symbol) {

        loadTradingView(
            data.symbol
        );
    }

    // ======================
    // SCREENER
    // ======================

    if (data.screener) {

        let html = "";

        data.screener.forEach(item => {

            let cls = "none";

            if (
                item.signal === "LONG"
            ) {
                cls = "long";
            }

            if (
                item.signal === "SHORT"
            ) {
                cls = "short";
            }

            html += `

            <tr>

                <td>${item.symbol}</td>

                <td class="${cls}">
                    ${item.signal}
                </td>

                <td>
                    ${item.long_score}
                </td>

                <td>
                    ${item.short_score}
                </td>

                <td>
                    ${item.trend}
                </td>

                <td>
                    ${item.confidence}%
                </td>

            </tr>

            `;
        });

        document.getElementById(
            'screenerBody'
        ).innerHTML = html;
    }
});
