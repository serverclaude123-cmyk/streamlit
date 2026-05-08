import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import ssl

# --- 1. CONFIG ---
B = st.secrets["BROKER"]
U = st.secrets["USER"]
P = st.secrets["PASS"]

st.set_page_config(page_title="Industrial Monitor", layout="wide")

# --- 2. STATE ---
if "data" not in st.session_state: st.session_state.data = {}
if "status" not in st.session_state: st.session_state.status = "Connecting to HiveMQ..."

# --- 3. CALLBACKS ---
def on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        st.session_state.status = "✅ CONNECTED"
        client.subscribe("hive/a")
    else:
        st.session_state.status = f"❌ REFUSED (RC: {rc})"

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode().strip()
        if payload.startswith('"') and payload.endswith('"'):
            payload = payload[1:-1]
        st.session_state.data = json.loads(payload)
    except Exception as e:
        st.session_state.data = {"Raw": msg.payload.decode()}

# --- 4. CONNECTION (No Cache to avoid sticking errors) ---
if 'mqtt_client' not in st.session_state:
    try:
        # Explicitly use protocol v3.1.1 for maximum compatibility
        c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
        c.username_pw_set(U, P)
        c.tls_set_context(ssl.create_default_context())
        c.on_connect = on_connect
        c.on_message = on_message
        
        c.connect(B, 8883, keepalive=60)
        c.loop_start()
        st.session_state.mqtt_client = c
    except Exception as e:
        st.session_state.status = f"⚠️ Setup Error: {str(e)}"

# --- 5. UI ---
st.title("🏭 Factory Monitor")
st.subheader(f"System Status: {st.session_state.status}")

if st.session_state.data:
    cols = st.columns(len(st.session_state.data))
    for i, (k, v) in enumerate(st.session_state.data.items()):
        cols[i].metric(label=k.upper(), value=v)
else:
    st.info("📡 Waiting for message... Ensure Node-RED is sending a JSON package to 'hive/a'.")

# --- 6. AUTO-REFRESH ---
time.sleep(2)
st.rerun()
