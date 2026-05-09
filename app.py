import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import ssl
import queue
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIG ---
BROKER = st.secrets["3cc93849ba9e403dba00237c7cc4cb5e.s1.eu.hivemq.cloud"]
USER = st.secrets["user2"]
PASS  = st.secrets["ServerClaude#1"]
SUPABASE_URL  = st.secrets["Shttps://mxorqtwurxzeqpydcqbw.supabase.co"]
SUPABASE_KEY  = st.secrets["sb_publishable_J3AGPX79fZR9Dr8SPMRBXg_npyuutZn"]
TABLE         = "electrical_log"
WIB           = timezone(timedelta(hours=7))

st.set_page_config(page_title="Industrial Monitor", layout="wide")

# --- 2. SUPABASE CLIENT (cached — one instance for the session) ---
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# --- 3. SESSION STATE ---
if "data"               not in st.session_state: st.session_state.data = {}
if "status"             not in st.session_state: st.session_state.status = "Connecting..."
if "msg_queue"          not in st.session_state: st.session_state.msg_queue = queue.Queue()
if "last_logged_minute" not in st.session_state: st.session_state.last_logged_minute = None

# --- 4. SUPABASE LOGGING ---
def log_to_supabase(data: dict):
    """Insert one row into Supabase with WIB timestamp."""
    now_str = datetime.now(WIB).isoformat()
    row = {"timestamp": now_str}

    for k, v in data.items():
        if k == "timestamp":
            continue
        try:
            row[k] = float(v)
        except (ValueError, TypeError):
            row[k] = str(v)

    try:
        supabase.table(TABLE).insert(row).execute()
    except Exception as e:
        st.session_state.status = f"⚠️ DB Error: {e}"

# --- 5. MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        st.session_state.status = "✅ CONNECTED"
        client.subscribe("hive/a")
    else:
        st.session_state.status = f"❌ REFUSED (RC: {rc})"

def on_message(client, userdata, msg):
    try:
        raw = msg.payload.decode().strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1].replace('\\"', '"')
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            userdata["queue"].put(parsed)
        else:
            userdata["queue"].put({"value": str(parsed)})
    except Exception as e:
        userdata["queue"].put({"Raw": msg.payload.decode(), "Error": str(e)})

# --- 6. MQTT CONNECTION ---
if "mqtt_client" not in st.session_state:
    try:
        msg_q = st.session_state.msg_queue
        c = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv311,
            userdata={"queue": msg_q}
        )
        c.username_pw_set(USER, PASS)
        c.tls_set_context(ssl.create_default_context())
        c.on_connect = on_connect
        c.on_message = on_message
        c.connect(BROKER, 8883, keepalive=60)
        c.loop_start()
        st.session_state.mqtt_client = c
    except Exception as e:
        st.session_state.status = f"⚠️ Setup Error: {e}"

# --- 7. DRAIN QUEUE + LOG EVERY 1 MINUTE ---
try:
    while True:
        new_data = st.session_state.msg_queue.get_nowait()
        st.session_state.data.update(new_data)
except queue.Empty:
    pass

if st.session_state.data:
    current_minute = datetime.now(WIB).strftime("%Y-%m-%d %H:%M")
    if current_minute != st.session_state.last_logged_minute:
        log_to_supabase(st.session_state.data)
        st.session_state.last_logged_minute = current_minute

# --- 8. UI ---
st.title("🏭 Factory Monitor")
st.subheader(f"System Status: {st.session_state.status}")

tab_live, tab_log, tab_chart = st.tabs(["📡 Live Monitor", "📋 Data Log", "📈 Trend Chart"])

# ── TAB 1: LIVE ──────────────────────────────────────────────────────────────
with tab_live:
    if st.session_state.data:
        items = [(k, v) for k, v in st.session_state.data.items() if k != "timestamp"]
        cols = st.columns(min(len(items), 4))
        for i, (k, v) in enumerate(items):
            col = cols[i % len(cols)]
            try:
                col.metric(label=k.upper(), value=f"{float(v):.2f}")
            except (ValueError, TypeError):
                col.metric(label=k.upper(), value=str(v))
    else:
        st.info("⏳ Waiting for data from Node-RED...")

    st.caption(f"Last updated: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')} WIB")

# ── TAB 2: DATA LOG ──────────────────────────────────────────────────────────
with tab_log:
    st.markdown("### 📋 Logged Records")

    # Date range filter
    col_from, col_to, col_fetch = st.columns([2, 2, 1])
    date_from = col_from.date_input("From", value=datetime.now(WIB).date())
    date_to   = col_to.date_input("To",   value=datetime.now(WIB).date())

    if col_fetch.button("🔍 Load", use_container_width=True):
        try:
            result = (
                supabase.table(TABLE)
                .select("*")
                .gte("timestamp", f"{date_from}T00:00:00+07:00")
                .lte("timestamp", f"{date_to}T23:59:59+07:00")
                .order("timestamp", desc=True)
                .limit(5000)
                .execute()
            )
            st.session_state.log_df = pd.DataFrame(result.data)
        except Exception as e:
            st.error(f"Query failed: {e}")

    if "log_df" in st.session_state and not st.session_state.log_df.empty:
        df = st.session_state.log_df.copy()

        # Convert timestamp to WIB-readable string
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["timestamp"] = df["timestamp"].dt.tz_convert(WIB).dt.strftime("%Y-%m-%d %H:%M:%S")

        col_info, col_dl = st.columns([3, 1])
        col_info.markdown(f"**{len(df)} records** found")
        col_dl.download_button(
            label="⬇️ Download CSV",
            data=df.to_csv(index=False).encode(),
            file_name=f"electrical_log_{date_from}_{date_to}.csv",
            mime="text/csv"
        )
        st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True, hide_index=True)
    else:
        st.info("Select a date range and click Load.")

# ── TAB 3: TREND CHART ───────────────────────────────────────────────────────
with tab_chart:
    st.markdown("### 📈 Parameter Trend")

    col_p, col_range = st.columns([2, 2])

    # Build column list from live data keys (excluding timestamp/id)
    param_options = [k for k in st.session_state.data.keys() if k not in ("timestamp", "id", "Error", "Raw")]
    if not param_options:
        param_options = ["voltage", "current", "power"]   # fallback defaults

    selected_param = col_p.selectbox("Parameter", param_options)
    time_range     = col_range.selectbox("Range", ["Last 1 hour", "Last 6 hours", "Last 24 hours", "Last 7 days", "Last 30 days"])

    range_map = {
        "Last 1 hour":   timedelta(hours=1),
        "Last 6 hours":  timedelta(hours=6),
        "Last 24 hours": timedelta(hours=24),
        "Last 7 days":   timedelta(days=7),
        "Last 30 days":  timedelta(days=30),
    }
    delta     = range_map[time_range]
    from_time = (datetime.now(WIB) - delta).isoformat()

    if st.button("📊 Load Chart"):
        try:
            result = (
                supabase.table(TABLE)
                .select(f"timestamp,{selected_param}")
                .gte("timestamp", from_time)
                .order("timestamp", desc=False)
                .limit(10000)
                .execute()
            )
            chart_df = pd.DataFrame(result.data)
            if not chart_df.empty and selected_param in chart_df.columns:
                chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"], utc=True)
                chart_df["timestamp"] = chart_df["timestamp"].dt.tz_convert(WIB)
                chart_df = chart_df.set_index("timestamp")
                chart_df[selected_param] = pd.to_numeric(chart_df[selected_param], errors="coerce")
                st.line_chart(chart_df[[selected_param]])
            else:
                st.warning("No data found for this range.")
        except Exception as e:
            st.error(f"Chart query failed: {e}")

# --- 9. AUTO-REFRESH ---
time.sleep(2)
st.rerun()
