import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import ssl
import queue
from datetime import datetime, timezone, timedelta

# --- 1. CONFIG ---
B = st.secrets["BROKER"]
U = st.secrets["USER"]
P = st.secrets["PASS"]

st.set_page_config(page_title="Industrial Monitor", layout="wide")

# --- 2. STATE ---
if "data" not in st.session_state:
    st.session_state.data = {}
if "status" not in st.session_state:
    st.session_state.status = "Connecting to HiveMQ..."

# Thread-safe queue: MQTT thread writes here, Streamlit reads here
if "msg_queue" not in st.session_state:
    st.session_state.msg_queue = queue.Queue()

# --- 3. CALLBACKS ---
def on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        st.session_state.status = "✅ CONNECTED"
        client.subscribe("hive/a")
    else:
        st.session_state.status = f"❌ REFUSED (RC: {rc})"

def on_message(client, userdata, msg):
    """Runs in MQTT background thread — only write to the queue here."""
    try:
        raw = msg.payload.decode().strip()

        # Handle double-encoded JSON: e.g. "{\"voltage\":999}" wrapped in extra quotes
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1].replace('\\"', '"')

        parsed = json.loads(raw)

        # If Node-RED sends a flat JSON object, use it directly
        if isinstance(parsed, dict):
            userdata["queue"].put(parsed)
        else:
            userdata["queue"].put({"value": str(parsed)})

    except Exception as e:
        userdata["queue"].put({"Raw": msg.payload.decode(), "Error": str(e)})

# --- 4. MQTT CONNECTION ---
if "mqtt_client" not in st.session_state:
    try:
        msg_q = st.session_state.msg_queue

        c = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv311,
            userdata={"queue": msg_q}   # pass queue via userdata — thread-safe
        )
        c.username_pw_set(U, P)
        c.tls_set_context(ssl.create_default_context())
        c.on_connect = on_connect
        c.on_message = on_message

        c.connect(B, 8883, keepalive=60)
        c.loop_start()
        st.session_state.mqtt_client = c

    except Exception as e:
        st.session_state.status = f"⚠️ Setup Error: {str(e)}"

# --- 5. DRAIN THE QUEUE into session state (runs every rerun) ---
try:
    while True:
        new_data = st.session_state.msg_queue.get_nowait()
        st.session_state.data.update(new_data)   # merge latest values
except queue.Empty:
    pass

# --- 6. UI ---
st.title("🏭 Factory Monitor")
st.subheader(f"System Status: {st.session_state.status}")

if st.session_state.data:
    # Show each key-value as a metric card
    items = list(st.session_state.data.items())
    cols = st.columns(min(len(items), 4))   # max 4 per row
    for i, (k, v) in enumerate(items):
        col = cols[i % len(cols)]
        # Try to display as number with 2 decimal places
        try:
            col.metric(label=k.upper(), value=f"{float(v):.2f}")
        except (ValueError, TypeError):
            col.metric(label=k.upper(), value=str(v))
else:
    st.info("⏳ Waiting for data... Make sure Node-RED Join node is sending JSON to 'hive/a'.")

jakarta_time = datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S')
st.caption(f"Last updated: {jakarta_time} WIB")

# --- 7. AUTO-REFRESH ---
time.sleep(2)
st.rerun()
