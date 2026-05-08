import streamlit as st
import paho.mqtt.client as mqtt
import json
import time

# --- CONFIG ---
BROKER = st.secrets["BROKER"]
USER = st.secrets["USER"]
PASS = st.secrets["PASS"]
TOPIC = "hive/a"

st.set_page_config(page_title="Industrial Monitor", layout="wide")

# Use st.session_state for status so it survives the rerun
if 'conn_log' not in st.session_state:
    st.session_state.conn_log = "Starting connection..."
if 'last_received' not in st.session_state:
    st.session_state.last_received = {}

# --- CALLBACKS ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.conn_log = "✅ Connected Successfully!"
    else:
        st.session_state.conn_log = f"❌ Connection Refused (RC: {rc})"

def on_message(client, userdata, msg):
    try:
        raw = msg.payload.decode().strip()
        # Handle stringified JSON
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        st.session_state.last_received = json.loads(raw)
    except Exception as e:
        st.session_state.last_received = {"Raw Data": msg.payload.decode()}

# --- CONNECTION LOGIC (NO CACHE FOR DEBUGGING) ---
if 'mqtt_client' not in st.session_state:
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        client.username_pw_set(USER, PASS)
        client.tls_set() # Mandatory for HiveMQ Cloud
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Connect and start background loop
        client.connect(BROKER, 8883, keepalive=60)
        client.subscribe(TOPIC)
        client.loop_start()
        
        st.session_state.mqtt_client = client
    except Exception as e:
        st.session_state.conn_log = f"⚠️ Setup Error: {str(e)}"

# --- UI ---
st.title("🏭 Factory Monitor")
st.info(f"Status: {st.session_state.conn_log}")

if st.session_state.last_received:
    data = st.session_state.last_received
    cols = st.columns(len(data))
    for i, (k, v) in enumerate(data.items()):
        cols[i].metric(label=k.upper(), value=v)
else:
    st.warning("Connected, but waiting for data on 'hive/a'...")

# Fast refresh to catch the 'on_connect' update
time.sleep(2)
st.rerun()
