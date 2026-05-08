import streamlit as st
import paho.mqtt.client as mqtt
import time

# --- CONFIG ---
BROKER = "3cc93849ba9e403dba00237c7cc4cb5e.s1.eu.hivemq.cloud"
PORT = 8883
USER = "user2"
PASS = "ServerClaude#1"
TOPIC = "hive/a"

# 1. THREAD-SAFE STORAGE
# We use a simple dictionary to hold the value outside the Streamlit state
if 'shared_data' not in st.session_state:
    st.session_state.shared_data = {"val": "Waiting for data..."}

st.set_page_config(page_title="Modbus Monitor", layout="centered")
st.title("🔋 Live Modbus Data")

# 2. THE CALLBACK
def on_message(client, userdata, msg):
    # Store the data in the dictionary
    # We use the 'userdata' to pass our dictionary into the thread safely
    userdata["val"] = msg.payload.decode()

# 3. CLIENT SETUP (Cached to prevent reconnect loops)
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

# Initialize the client and pass our shared dictionary
mqtt_client = setup_mqtt(st.session_state.shared_data)

# 4. UI DISPLAY
# Pull the value from our shared dictionary
current_value = st.session_state.shared_data["val"]
st.metric(label="Modbus Reading", value=current_value)

st.divider()
st.caption(f"Status: Connected to {TOPIC}")

# 5. REFRESH LOOP
time.sleep(1)
st.rerun()