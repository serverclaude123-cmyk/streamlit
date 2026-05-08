import streamlit as st
import paho.mqtt.client as mqtt
import json
import time

# --- CONFIG ---
# Best Practice: Use st.secrets if deploying to the cloud
BROKER = st.secrets["BROKER"]
PORT = 8883
USER = st.secrets["USER"]
PASS = st.secrets["PASS"]
TOPIC = "hive/a"

st.set_page_config(page_title="Industrial Monitor", layout="wide")

# 1. Shared Storage (Using a list to avoid some SessionState quirks)
if 'data_store' not in st.session_state:
    st.session_state.data_store = {"payload": {}}

# 2. Advanced Callback
def on_message(client, userdata, msg):
    try:
        # Clean the string (remove any accidental quotes at start/end)
        raw_payload = msg.payload.decode().strip()
        if raw_payload.startswith('"') and raw_payload.endswith('"'):
            raw_payload = raw_payload[1:-1]
        
        # Parse JSON
        parsed_data = json.loads(raw_payload)
        st.session_state.data_store["payload"] = parsed_data
    except Exception as e:
        # If it's not JSON, just show the raw string
        st.session_state.data_store["payload"] = {"Raw Message": msg.payload.decode()}

# 3. Singleton MQTT Client
@st.cache_resource
def init_mqtt(_shared_dict):
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=_shared_dict)
    client.username_pw_set(USER, PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(BROKER, 8883)
    client.subscribe(TOPIC)
    client.loop_start()
    return client

mqtt_conn = init_mqtt(st.session_state.data_store)

# 4. Dashboard UI
st.title("🏭 Real-Time Factory Monitor")
display_data = st.session_state.data_store.get("payload", {})

if display_data:
    # Auto-generate boxes for Current, Voltage, and SABDA/IR
    cols = st.columns(len(display_data))
    for i, (key, val) in enumerate(display_data.items()):
        with cols[i]:
            # Formatting numbers for readability
            if isinstance(val, (int, float)):
                st.metric(label=key.replace("_", " ").upper(), value=f"{val:,.2f}")
            else:
                st.metric(label=key.upper(), value=val)
else:
    st.info("📡 Connecting to HiveMQ... Please trigger Node-RED.")

# 5. Refresh Logic
time.sleep(2)
st.rerun()
