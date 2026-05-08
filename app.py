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

if 'last_received' not in st.session_state:
    st.session_state.last_received = {}

# --- THE FIX: SHARED CONNECTION STATUS ---
if 'conn_log' not in st.session_state:
    st.session_state.conn_log = "Initializing..."

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.conn_log = "✅ Connected to HiveMQ"
    else:
        st.session_state.conn_log = f"❌ Connection Refused (Error Code: {rc})"

def on_message(client, userdata, msg):
    try:
        raw = msg.payload.decode().strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        st.session_state.last_received = json.loads(raw)
    except:
        st.session_state.last_received = {"Raw": msg.payload.decode()}

@st.cache_resource
def start_mqtt():
    # Use version 2 of the callback API
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(USER, PASS)
    c.tls_set() # Required for HiveMQ Cloud Port 8883
    c.on_connect = on_connect
    c.on_message = on_message
    
    try:
        # 60 second keepalive to prevent the cloud from dropping the connection
        c.connect(BROKER, 8883, keepalive=60)
        c.subscribe(TOPIC)
        c.loop_start()
        return c
    except Exception as e:
        st.session_state.conn_log = f"⚠️ Network Error: {str(e)}"
        return None

client = start_mqtt()

# --- UI ---
st.title("🏭 Factory Monitor")
st.info(f"Connection Status: {st.session_state.conn_log}")

if st.session_state.last_received:
    data = st.session_state.last_received
    cols = st.columns(len(data))
    for i, (k, v) in enumerate(data.items()):
        cols[i].metric(label=k.upper(), value=v)
else:
    st.warning("No data package received on 'hive/a' yet.")

time.sleep(2)
st.rerun()
