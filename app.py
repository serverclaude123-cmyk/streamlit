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

# 1. Persistent Storage (Cross-run storage)
if 'last_received' not in st.session_state:
    st.session_state.last_received = {}
if 'conn_status' not in st.session_state:
    st.session_state.conn_status = "Disconnected"

# 2. Optimized Callback
def on_message(client, userdata, msg):
    try:
        raw = msg.payload.decode().strip()
        # Clean up double-encoded JSON if necessary
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        
        data = json.loads(raw)
        # Update session state directly
        st.session_state.last_received = data
    except Exception as e:
        st.session_state.last_received = {"Error": str(e), "Raw": msg.payload.decode()}

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.conn_status = "✅ Connected to HiveMQ"
    else:
        st.session_state.conn_status = f"❌ Connection Failed (Code {rc})"

# 3. Connection Setup
@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USER, PASS)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER, 8883, keepalive=60)
        client.subscribe(TOPIC)
        client.loop_start()
        return client
    except Exception as e:
        st.error(f"Connect Error: {e}")
        return None

client = get_mqtt_client()

# 4. UI Layout
st.title("🏭 Factory Monitor")
st.write(f"Status: {st.session_state.conn_status}")

if st.session_state.last_received:
    data = st.session_state.last_received
    cols = st.columns(len(data))
    for i, (k, v) in enumerate(data.items()):
        cols[i].metric(label=k.upper(), value=v)
else:
    st.warning("Connected, but no data received yet. Is Node-RED sending to 'hive/a'?")

# 5. Slow down the loop
# If the loop is too fast, the background thread can't update the UI thread
time.sleep(3) 
st.rerun()
