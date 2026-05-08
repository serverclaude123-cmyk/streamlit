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

# 1. GLOBAL STORAGE (The Bridge)
# This lives outside of Streamlit's refresh cycle
if 'global_metrics' not in globals():
    globals()['global_metrics'] = {}

# 2. THE CALLBACK (Writes to Global)
def on_message(client, userdata, msg):
    try:
        raw_payload = msg.payload.decode().strip()
        # Remove surrounding quotes if Node-RED sent a "stringified" string
        if raw_payload.startswith('"') and raw_payload.endswith('"'):
            raw_payload = raw_payload[1:-1]
        
        parsed_data = json.loads(raw_payload)
        globals()['global_metrics'] = parsed_data
    except Exception as e:
        globals()['global_metrics'] = {"Error": str(e), "Raw": msg.payload.decode()}

# 3. THE CLIENT (Cached Singleton)
@st.cache_resource
def init_mqtt():
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USER, PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(BROKER, 8883)
    client.subscribe(TOPIC)
    client.loop_start()
    return client

mqtt_conn = init_mqtt()

# 4. THE UI (Reads from Global)
st.title("🏭 Real-Time Factory Monitor")

display_data = globals()['global_metrics']

if display_data:
    # Handle both Dictionary and single values
    if isinstance(display_data, dict):
        cols = st.columns(len(display_data))
        for i, (key, val) in enumerate(display_data.items()):
            with cols[i]:
                st.metric(label=key.upper(), value=val)
    else:
        st.metric(label="LATEST DATA", value=display_data)
else:
    st.info("📡 Connected. Waiting for JSON package from Node-RED...")
    st.caption("Tip: Ensure your Node-RED Join node is sending a single JSON object.")

# 5. REFRESH
time.sleep(2)
st.rerun()
