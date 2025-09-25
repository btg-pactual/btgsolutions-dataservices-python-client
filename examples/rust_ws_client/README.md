# rust_ws_client — BTG Market Data WebSocket Debugger

A tiny, focused Rust tool to **authenticate**, **connect**, and **exercise** BTG’s market data WebSocket for **options book** updates. It helps you:

- Fetch the **full list of instruments** via `{"action":"available_to_subscribe"}`
- **Subscribe to all** instruments with `n=1` and `initial_snapshot=true`
- Stream messages and compute **live stats** with **sliding-window** throughput (1s / 10s / 60s)
- Choose what to print: **raw WS messages**, **stats only**, or **both**

Perfect for debugging connectivity, validating token handling (`Sec-WebSocket-Protocol`), and monitoring stream coverage & throughput.

---

## Features

- ✅ REST auth (`/api/v2/authenticate`) with `api_key` and `client_id`
- ✅ WebSocket handshake to `/stream/v2/marketdata/book/options`
  - JWT is sent in **`Sec-WebSocket-Protocol`** (no `Bearer ` prefix)
- ✅ `available_to_subscribe` to get all instrument **symbols**
- ✅ Subscribe to **all** instruments with:
  ```json
  {
    "action":"subscribe",
    "params": {
      "tickers":[...],
      "n":1,
      "initial_snapshot": true
    }
  }
  ```
- ✅ Tracks:
  - total messages, live book messages, snapshot messages
  - **coverage**: instruments with any **live** event, any **snapshot**, and **union** (either)
- ✅ **Sliding-window throughput**: 1s / 10s / 60s (msgs/s, instruments/s)
- ✅ Terminal-friendly **ASCII table** stats, every 5 seconds
- ✅ Asynchronous non-blocking printing via an **mpsc** queue
- ✅ Configurable **print mode**: `stats`, `ws`, or `both`

---

## Repo Layout (minimal)

```
rust_ws_client/
├── Cargo.toml
├── config.toml          # you create this (see below)
└── src/
    └── main.rs          # the program
```

---

## Requirements

- **Rust** 1.90+ (recommended)
- Network access to:
  - `https://dataservices.btgpactualsolutions.com/api/v2/authenticate`
  - `wss://dataservices.btgpactualsolutions.com/stream/v2/marketdata/book/options`

---

## Dependencies (Cargo.toml)

```toml
[dependencies]
tokio = { version = "1.39", features = ["rt-multi-thread", "macros"] }
reqwest = { version = "0.12", features = ["json", "rustls-tls"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio-tungstenite = { version = "0.21", features = ["rustls-tls-webpki-roots"] }
anyhow = "1.0"
url = "2.5"
futures = "0.3"
toml = "0.8"
```

---

## Configuration

Create a `config.toml` in the project root:

```toml
# config.toml
api_key   = "PASTE_YOUR_REAL_API_KEY_HERE"
client_id = "PASTE_YOUR_REAL_CLIENT_ID_HERE"

# What to print on stdout:
#  - "stats" : only the ASCII stats table every 5 seconds
#  - "ws"    : only raw WebSocket JSON payloads
#  - "both"  : both stats and raw WS messages
print_mode = "both"
```

### What each knob does

- `api_key` — Your credential from BTG.
- `client_id` — Your client ID.
- `print_mode` — Controls console noise vs visibility:
  - `stats` is ideal for long runs and performance monitoring.
  - `ws` is ideal for protocol debugging (payloads).
  - `both` for full visibility (can be very chatty).

---

## How to Run

```bash
# from the project root
cargo run --release
```

You should see:

1) Auth success and token prefix
2) WebSocket handshake response `101 Switching Protocols`
3) Confirmation of instruments fetched & subscription
4) Either WS messages, the stats table, or both — based on `print_mode`

---

## The Stats Table — How to Read It

Every 5 seconds, you’ll see a table like:

```
[STATS @   25.0s]
+----------------------+------------------------------+------------------------------+------------------------------+
| Section              |            1s window         |           10s window         |            60s window         |
+----------------------+------------------------------+------------------------------+------------------------------+
| Msgs total/s         |       250.0 /s               |       230.5 /s               |       180.2 /s               |
| Msgs live/s          |       190.4 /s               |       175.9 /s               |       140.1 /s               |
| Msgs snapshot/s      |        59.6 /s               |        54.6 /s               |        40.1 /s               |
| Inst live/s          |         3.200 /s             |         2.850 /s             |         1.900 /s             |
| Inst snapshot/s      |         4.100 /s             |         3.200 /s             |         2.300 /s             |
+----------------------+------------------------------+------------------------------+------------------------------+

+----------------------+------------------------------+
| Totals/Coverage      | Values                       |
+----------------------+------------------------------+
| Total messages        |      15234 (live:       9876, snap:       5358) |
| Instruments (live)    |    840/1000   84.00%            |
| Instruments (snap)    |   1000/1000  100.00%            |
| Instruments (union)   |   1000/1000  100.00%            |
| Print buffer          | remaining  9785 / cap  10000    |
+----------------------+------------------------------+
```

### Top block: sliding-window throughput
- **Msgs total/s**: All WS text messages per second (live + snapshot).
- **Msgs live/s**: Only `{"ev":"book", ...}` per second.
- **Msgs snapshot/s**: Only initial snapshot wrappers per second.
- **Inst live/s**: New instruments per second that received their **first live** update in the window.
- **Inst snapshot/s**: New instruments per second that received their **first snapshot** in the window.
- Columns show **1s**, **10s**, and **60s** sliding windows over the last minute of activity.

### Bottom block: totals and coverage
- **Total messages**: Cumulative counts (since program start) for all, live, and snapshot messages.
- **Instruments (live)**: Distinct `symb` that have received **at least one live** `book` update (plus coverage vs. total available).
- **Instruments (snap)**: Distinct `symb` that have received **at least one initial snapshot**.
- **Instruments (union)**: Distinct `symb` that have received **either** snapshot or live (overall coverage).
- **Print buffer**: Remaining slots in the async print queue. Near zero means stdout can’t keep up.

---

## Security Notes

- Your `api_key` lives in **`config.toml`**. Treat it as sensitive; don’t commit it.
- The JWT is sent in `Sec-WebSocket-Protocol`. Anyone with packet capture could read it — use secure networks.

---

## FAQ

**Q: Can I switch to trades or stocks?**  
A: Yes — change the WS URL to the desired channel (e.g., `/stream/v2/marketdata/trade/options`) and adjust the subscription payload if the schema differs.

**Q: Can I run multiple channels in parallel?**  
A: Yes — spawn multiple tasks (one per channel), each with its own connection and stats (or share a global aggregator).

---

## Troubleshooting

### OpenSSL build errors (`openssl-sys v0.9.x`)

If you see:

```
warning: openssl-sys@0.9.x: Could not find directory of OpenSSL installation
error: failed to run custom build command for `openssl-sys v0.9.x`
```

It means one of the dependencies is trying to compile against OpenSSL (via the `native-tls` feature).

There are **two ways** to fix it:

#### Option A — use Rustls (recommended)  
Force `reqwest` and `tokio-tungstenite` to use **rustls** instead of `native-tls`:

```toml
# Cargo.toml
reqwest = { version = "0.12", default-features = false, features = ["json", "rustls-tls"] }
tokio-tungstenite = { version = "0.21", default-features = false, features = ["rustls-tls-webpki-roots"] }
```

Then clean and rebuild:

```bash
cargo clean
rm -f Cargo.lock
cargo build --release
```

This avoids OpenSSL entirely.

#### Option B — install OpenSSL system libraries  
If you prefer to keep using `native-tls` (or a dependency forces it), install OpenSSL development headers:

- **Ubuntu/Debian:**
  ```bash
  sudo apt-get update
  sudo apt-get install -y pkg-config libssl-dev build-essential
  ```
- **Fedora/RHEL/CentOS:**
  ```bash
  sudo dnf install -y pkgconf-pkg-config openssl-devel gcc make
  ```
- **Alpine Linux:**
  ```bash
  sudo apk add openssl-dev pkgconfig build-base
  ```
- **macOS (Homebrew):**
  ```bash
  brew install openssl@3
  export OPENSSL_DIR="$(brew --prefix openssl@3)"
  export PKG_CONFIG_PATH="$OPENSSL_DIR/lib/pkgconfig"
  ```
- **Windows:** easiest is to avoid OpenSSL and use Rustls. If you must, install via [vcpkg](https://github.com/microsoft/vcpkg).

After installing the libraries, re-run:

```bash
cargo build --release
```

---
