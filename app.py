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
st.title("🏭 Real-Time Industrial Dashboard")

# 1. Initialize Thread-Safe Storage
# We use a nested dictionary to ensure 'data' always exists
if 'shared_data' not in st.session_state:
    st.session_state.shared_data = {"data": {}}

# 2. Callback with JSON Parsing
def on_message(client, userdata, msg):
    try:
        # Parse the JSON string from Node-RED back into a Python Dictionary
        payload = json.loads(msg.payload.decode())
        userdata["data"] = payload
    except Exception as e:
        # Fallback if the data isn't JSON
        userdata["data"] = {"Raw Message": msg.payload.decode()}

# 3. Cached MQTT Client
@st.cache_resource
def setup_mqtt(_data_dict):
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=_data_dict)
    client.username_pw_set(USER, PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.subscribe(TOPIC)
    client.loop_start()
    return client

mqtt_client = setup_mqtt(st.session_state.shared_data)

# 4. Safe UI Rendering
# Use .get() to avoid KeyErrors if the dictionary is temporarily empty
current_dict = st.session_state.shared_data.get("data", {})

if current_dict:
    # This creates a grid of metrics automatically based on your JSON keys
    cols = st.columns(min(len(current_dict), 4)) 
    for index, (label, value) in enumerate(current_dict.items()):
        with cols[index % len(cols)]:
            st.metric(label=label.upper(), value=value)
else:
    st.warning("📡 Waiting for synchronized data package from Node-RED...")

st.divider()
st.caption(f"Listening to: {TOPIC} | System Time: {time.strftime('%H:%M:%S')}")

# 5. Fast Refresh
time.sleep(1)
st.rerun()
