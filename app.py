import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import certifi

# --- 1. PULL CREDENTIALS FROM SECRETS ---
try:
    B = st.secrets["BROKER"]
    U = st.secrets["USER"]
    P = st.secrets["PASS"]
except Exception as e:
    st.error(f"Secrets Error: {e}")
    st.stop()

# --- 2. INITIALIZE SESSION STATE ---
if "data" not in st.session_state:
    st.session_state.data = {}
if "status" not in st.session_state:
    st.session_state.status = "Connecting..."

# --- 3. MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        st.session_state.status = "✅ CONNECTED"
    else:
        st.session_state.status = f"❌ CONNECTION FAILED (RC: {rc})"

def on_message(client, userdata, msg):
    try:
        raw_payload = msg.payload.decode().strip()
        # Clean stringified JSON if needed
        if raw_payload.startswith('"') and raw_payload.endswith('"'):
            raw_payload = raw_payload[1:-1]
        st.session_state.data = json.loads(raw_payload)
    except Exception as e:
        st.session_state.data = {"Error": str(e), "Raw": msg.payload.decode()}

# --- 4. MQTT CLIENT (CACHED) ---
@st.cache_resource
def get_mqtt_client():
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(U, P)
    c.tls_set(ca_certs=certifi.where()) # Uses certifi to handle SSL
    c.on_connect = on_connect
    c.on_message = on_message
    
    try:
        c.connect(B, 8883, keepalive=60)
        c.subscribe("hive/a")
        c.loop_start()
        return c
    except Exception as e:
        st.error(f"Network Error: {e}")
        return None

# Trigger the connection
mqtt_client = get_mqtt_client()

# --- 5. DASHBOARD UI ---
st.title("🏭 Factory Real-Time Monitor")
st.subheader(f"System Status: {st.session_state.status}")

if st.session_state.data:
    # This automatically creates columns for Voltage, Current, etc.
    metrics = st.session_state.data
    cols = st.columns(len(metrics))
    
    for i, (key, value) in enumerate(metrics.items()):
        with cols[i]:
            st.metric(label=key.upper(), value=value)
else:
    st.info("📡 Waiting for data from Node-RED... Make sure all 3 inputs are triggered.")

# --- 6. AUTO-REFRESH ---
time.sleep(2)
st.rerun()
