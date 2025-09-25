use anyhow::Result;
use futures::{SinkExt, StreamExt};
use serde::Deserialize;
use serde_json::{json, Value};
use std::collections::{HashSet, VecDeque};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tokio::sync::mpsc;
use tokio_tungstenite::{
    connect_async,
    tungstenite::{
        client::IntoClientRequest,
        http::HeaderValue,
        protocol::Message,
    },
};

// ===== Config parsing =====

#[derive(Deserialize)]
struct Config {
    api_key: String,
    client_id: String,
    /// "stats" | "ws" | "both"
    #[serde(default = "default_print_mode")]
    print_mode: String,
}

fn default_print_mode() -> String { "both".into() }

#[derive(Deserialize)]
struct AuthResponse {
    #[serde(rename = "AccessToken")]
    access_token: String,
}

#[derive(Deserialize)]
struct AvailableResp {
    ev: String,
    status: String,
    message: Vec<String>,
}

// ===== Sliding-window snapshot =====

#[derive(Clone, Copy)]
struct Snap {
    t: Instant,
    total_msgs: usize,
    live_msgs: usize,
    snap_msgs: usize,
    live_insts: usize,
    snap_insts: usize,
    union_insts: usize,
}

const PRINT_BUFFER_SIZE: usize = 10_000; // channel capacity we allocate

#[tokio::main]
async fn main() -> Result<()> {
    // ---- Load config
    let cfg: Config = {
        let txt = std::fs::read_to_string("config.toml")?;
        toml::from_str(&txt)?
    };

    // ---- Auth
    let auth_url = "https://dataservices.btgpactualsolutions.com/api/v2/authenticate";
    let client = reqwest::Client::new();
    let body = json!({ "api_key": cfg.api_key, "client_id": cfg.client_id });
    let resp = client.post(auth_url).json(&body).send().await?;
    let txt = resp.text().await?;
    let token: String = serde_json::from_str::<AuthResponse>(&txt)
        .map(|parsed| parsed.access_token)
        .unwrap_or_else(|_| txt.trim().to_string());
    println!("Got token (prefix): {}", &token[..20.min(token.len())]);

    // ---- Connect WS (book/options)
    let ws_url = "wss://dataservices.btgpactualsolutions.com/stream/v2/marketdata/book/options";
    let mut req = ws_url.into_client_request()?;
    req.headers_mut().insert(
        "Sec-WebSocket-Protocol",
        HeaderValue::from_str(&token)?,
    );
    let (mut ws, _resp) = connect_async(req).await?;
    println!("Connected to book/options.");

    // ---- Ask availability
    ws.send(Message::Text(r#"{"action":"available_to_subscribe"}"#.into())).await?;

    // ---- Async printer
    let (print_tx, mut print_rx) = mpsc::channel::<String>(PRINT_BUFFER_SIZE);
    tokio::spawn(async move { while let Some(line) = print_rx.recv().await { println!("{line}"); } });

    // ---- Read availability list
    let instruments: Vec<String>;
    loop {
        if let Some(msg) = ws.next().await {
            if let Ok(Message::Text(txt)) = msg {
                if let Ok(parsed) = serde_json::from_str::<AvailableResp>(&txt) {
                    if parsed.ev == "available_to_subscribe" && parsed.status == "success" {
                        instruments = parsed.message;
                        break;
                    }
                }
                if cfg.print_mode != "stats" { let _ = print_tx.try_send(format!("WS: {txt}")); }
            }
        }
    }
    let total_instruments = instruments.len();
    print_tx.send(format!("Got {total_instruments} instruments.")).await.ok();

    // ---- Subscribe (n=1, initial_snapshot=true) to ALL instruments
    let subscribe_msg = json!({
        "action": "subscribe",
        "params": { "tickers": instruments.clone(), "n": 1, "initial_snapshot": true }
    });
    ws.send(Message::Text(subscribe_msg.to_string())).await?;
    print_tx.send("Sent subscribe for all instruments.".into()).await.ok();

    // ---- Shared state for stats
    let live_instruments: Arc<Mutex<HashSet<String>>> = Arc::new(Mutex::new(HashSet::new())); // seen in live "book"
    let snap_instruments: Arc<Mutex<HashSet<String>>> = Arc::new(Mutex::new(HashSet::new())); // seen in "get_last_event"

    let total_msgs = Arc::new(Mutex::new(0usize)); // all WS text messages
    let live_msgs   = Arc::new(Mutex::new(0usize)); // live "book"
    let snap_msgs   = Arc::new(Mutex::new(0usize)); // "get_last_event" snapshots

    let timeline = Arc::new(Mutex::new(VecDeque::<Snap>::new()));
    let start = Instant::now();

    // ---- Stats task: prints every 5s as a table, with sliding windows 1s/10s/60s
    if cfg.print_mode == "stats" || cfg.print_mode == "both" {
        let live_instruments_stats = Arc::clone(&live_instruments);
        let snap_instruments_stats = Arc::clone(&snap_instruments);
        let total_msgs_stats = Arc::clone(&total_msgs);
        let live_msgs_stats  = Arc::clone(&live_msgs);
        let snap_msgs_stats  = Arc::clone(&snap_msgs);
        let timeline_stats   = Arc::clone(&timeline);
        let print_tx_stats   = print_tx.clone();

        tokio::spawn(async move {
            loop {
                tokio::time::sleep(Duration::from_secs(5)).await;
                let now = Instant::now();

                // current counters
                let tm = *total_msgs_stats.lock().unwrap();
                let lm = *live_msgs_stats.lock().unwrap();
                let sm = *snap_msgs_stats.lock().unwrap();

                let li_set = live_instruments_stats.lock().unwrap().clone();
                let si_set = snap_instruments_stats.lock().unwrap().clone();
                let li = li_set.len();
                let si = si_set.len();
                let union_insts = li_set.union(&si_set).count();

                // push new snapshot; keep ~60s
                {
                    let mut tl = timeline_stats.lock().unwrap();
                    tl.push_back(Snap {
                        t: now,
                        total_msgs: tm,
                        live_msgs: lm,
                        snap_msgs: sm,
                        live_insts: li,
                        snap_insts: si,
                        union_insts,
                    });
                    while let Some(front) = tl.front() {
                        if now.duration_since(front.t).as_secs() > 60 { tl.pop_front(); } else { break; }
                    }
                }

                // compute sliding-window rates
                let (mt1, ml1, ms1, il1, is1) = calc_rates(&timeline_stats, now, 1, tm, lm, sm, li, si, union_insts);
                let (mt10, ml10, ms10, il10, is10) = calc_rates(&timeline_stats, now, 10, tm, lm, sm, li, si, union_insts);
                let (mt60, ml60, ms60, il60, is60) = calc_rates(&timeline_stats, now, 60, tm, lm, sm, li, si, union_insts);

                // render table
                let table = render_stats_table(
                    now.duration_since(start),
                    tm, lm, sm,
                    li, si, union_insts, total_instruments,
                    (mt1, mt10, mt60),
                    (ml1, ml10, ml60),
                    (ms1, ms10, ms60),
                    (il1, il10, il60),
                    (is1, is10, is60),
                    PRINT_BUFFER_SIZE,
                    print_tx_stats.capacity(),
                );
                let _ = print_tx_stats.try_send(table);
            }
        });
    }

    // ---- WS loop
    while let Some(msg) = ws.next().await {
        if let Ok(Message::Text(txt)) = msg {
            *total_msgs.lock().unwrap() += 1;

            if let Ok(v) = serde_json::from_str::<Value>(&txt) {
                if let Some(ev) = v.get("ev").and_then(|x| x.as_str()) {
                    match ev {
                        // live book message
                        "book" => {
                            *live_msgs.lock().unwrap() += 1;
                            if let Some(symb) = v.get("symb").and_then(|x| x.as_str()) {
                                live_instruments.lock().unwrap().insert(symb.to_string());
                            }
                        }
                        // initial snapshot wrapper
                        "get_last_event" => {
                            if v.get("status").and_then(|x| x.as_str()) == Some("success") {
                                if let Some(m) = v.get("message") {
                                    if m.get("ev").and_then(|x| x.as_str()) == Some("book") {
                                        *snap_msgs.lock().unwrap() += 1;
                                        if let Some(symb) = m.get("symb").and_then(|x| x.as_str()) {
                                            snap_instruments.lock().unwrap().insert(symb.to_string());
                                        }
                                    }
                                }
                            }
                        }
                        _ => {}
                    }
                }
            }

            if cfg.print_mode == "ws" || cfg.print_mode == "both" {
                let _ = print_tx.try_send(format!("WS: {txt}"));
            }
        }
    }

    Ok(())
}

// ===== Helpers =====

fn calc_rates(
    timeline_stats: &Arc<Mutex<VecDeque<Snap>>>,
    now: Instant,
    secs: u64,
    tm: usize, lm: usize, sm: usize,
    li: usize, si: usize, union_insts: usize,
) -> (f64, f64, f64, f64, f64) {
    let tl = timeline_stats.lock().unwrap();
    // select base snapshot: oldest ≥ secs ago, else earliest
    let mut base = None;
    for s in tl.iter().rev() {
        if now.duration_since(s.t).as_secs() >= secs { base = Some(*s); break; }
    }
    if base.is_none() {
        if let Some(first) = tl.front() { base = Some(*first); }
    }
    if let Some(b) = base {
        let dt = now.duration_since(b.t).as_secs_f64().max(1.0);
        let mps_total = (tm.saturating_sub(b.total_msgs)) as f64 / dt;
        let mps_live  = (lm.saturating_sub(b.live_msgs )) as f64 / dt;
        let mps_snap  = (sm.saturating_sub(b.snap_msgs )) as f64 / dt;
        let ips_live  = (li.saturating_sub(b.live_insts)) as f64 / dt;
        let _ips_union = (union_insts.saturating_sub(b.union_insts)) as f64 / dt; // unused, but handy if needed
        let ips_snap  = (si.saturating_sub(b.snap_insts)) as f64 / dt;
        (mps_total, mps_live, mps_snap, ips_live, ips_snap)
    } else {
        (0.0, 0.0, 0.0, 0.0, 0.0)
    }
}

fn render_stats_table(
    elapsed: Duration,
    tm: usize, lm: usize, sm: usize,
    li: usize, si: usize, ui: usize, total: usize,
    m_total: (f64, f64, f64),
    m_live:  (f64, f64, f64),
    m_snap:  (f64, f64, f64),
    i_live:  (f64, f64, f64),
    i_snap:  (f64, f64, f64),
    buf_cap: usize,
    buf_rem: usize,
) -> String {
    let cov_live = pct(li, total);
    let cov_snap = pct(si, total);
    let cov_union = pct(ui, total);

    let mut s = String::new();
    let brk = "+----------------------+------------------------------+------------------------------+------------------------------+\n";
    s.push_str(&format!("\n[STATS @ {:>6.1}s]\n", elapsed.as_secs_f64()));
    s.push_str(brk);
    s.push_str("| Section              |            1s window         |           10s window         |            60s window         |\n");
    s.push_str(brk);
    s.push_str(&row_rate("Msgs total/s",   m_total));
    s.push_str(&row_rate("Msgs live/s",    m_live));
    s.push_str(&row_rate("Msgs snapshot/s",m_snap));
    s.push_str(&row_rate("Inst live/s",    i_live));
    s.push_str(&row_rate("Inst snapshot/s",i_snap));
    s.push_str(brk);

    let brk2 = "+----------------------+------------------------------+\n";
    s.push_str(brk2);
    s.push_str("| Totals/Coverage      | Values                       |\n");
    s.push_str(brk2);
    s.push_str(&format!("| Total messages        | {:>10} (live: {:>10}, snap: {:>10}) |\n", tm, lm, sm));
    s.push_str(&format!("| Instruments (live)    | {:>5}/{:<5}  {:>6.2}%           |\n", li, total, cov_live));
    s.push_str(&format!("| Instruments (snap)    | {:>5}/{:<5}  {:>6.2}%           |\n", si, total, cov_snap));
    s.push_str(&format!("| Instruments (union)   | {:>5}/{:<5}  {:>6.2}%           |\n", ui, total, cov_union));
    s.push_str(&format!("| Print buffer          | remaining {:>5} / cap {:>5}     |\n", buf_rem, buf_cap));
    s.push_str(brk2);

    s
}

fn row_rate(label: &str, (r1, r10, r60): (f64, f64, f64)) -> String {
    format!("| {:<20} | {:>10.1} /s             | {:>10.1} /s             | {:>10.1} /s             |\n",
        label, r1, r10, r60)
}

fn pct(n: usize, d: usize) -> f64 {
    if d == 0 { 0.0 } else { (n as f64) * 100.0 / (d as f64) }
}
