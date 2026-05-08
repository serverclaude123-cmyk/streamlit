import streamlit as st
import paho.mqtt.client as mqtt
import json
import time

# --- PULL CREDENTIALS ---
try:
    B = st.secrets["BROKER"]
    U = st.secrets["USER"]
    P = st.secrets["PASS"]
    st.success("✅ Secrets loaded from Streamlit settings")
except Exception as e:
    st.error(f"❌ Secrets Error: {e}. Check your Advanced Settings!")
    st.stop()

# --- STATE ---
if "data" not in st.session_state:
    st.session_state.data = {}
if "status" not in st.session_state:
    st.session_state.status = "Disconnected"

# --- MQTT HANDLERS ---
def on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        st.session_state.status = "✅ CONNECTED"
    else:
        st.session_state.status = f"❌ FAILED (Code {rc})"

def on_message(client, userdata, msg):
    try:
        st.session_state.data = json.loads(msg.payload.decode())
    except:
        st.session_state.data = {"Raw": msg.payload.decode()}

# --- MAIN LOGIC ---
st.title("Industrial Dashboard")
st.subheader(f"Status: {st.session_state.status}")

@st.cache_resource
def get_client():
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(U, P)
    c.tls_set()
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(B, 8883)
    c.subscribe("hive/a")
    c.loop_start()
    return c

client = get_client()

# --- DISPLAY ---
if st.session_state.data:
    st.write("### Live Metrics")
    st.json(st.session_state.data) # Show raw JSON first to prove it's working
else:
    st.info("Waiting for first message from Node-RED...")

time.sleep(2)
st.rerun()
