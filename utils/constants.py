PAPER = "paper"
LIVE = "live"

PAPER_KEY_ENV_VAR = "ALPACA_PAPER_KEY"
PAPER_SECRET_ENV_VAR = "ALPACA_PAPER_SECRET"

LIVE_KEY_ENV_VAR = "ALPACA_LIVE_KEY"
LIVE_SECRET_ENV_VAR = "ALPACA_LIVE_SECRET"

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"

LIVE_ENDPOINT = "https://api.alpaca.markets"

DATA_FEED = "SIP"

COST_TRACE = "cost_trace"
MA_TRACE = "ma_trace"
PSAR_TRACE = "psar_trace"

TRACE_MODES = {
    COST_TRACE: "lines",
    MA_TRACE: "lines",
    PSAR_TRACE: "markers",
}
