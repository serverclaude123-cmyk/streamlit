import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import ssl

# --- 1. SECRETS ---
B = st.secrets["BROKER"]
U = st.secrets["USER"]
P = st.secrets["PASS"]

# --- 2. STATE ---
if "data" not in st.session_state: st.session_state.data = {}
if "status" not in st.session_state: st.session_state.status = "Initializing..."

# --- 3. CALLBACKS ---
def on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        st.session_state.status = "✅ CONNECTED"
        client.subscribe("hive/a")
    else:
        st.session_state.status = f"❌ REFUSED (RC: {rc})"

def on_message(client, userdata, msg):
    try:
        st.session_state.data = json.loads(msg.payload.decode())
    except:
        st.session_state.data = {"Raw": msg.payload.decode()}

# --- 4. THE CONNECTION ---
@st.cache_resource
@st.cache_resource
def get_mqtt():
    # Keep it simple: VERSION2 of the API, using default protocol
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(U, P)
    
    context = ssl.create_default_context()
    c.tls_set_context(context)
    
    c.on_connect = on_connect
    c.on_message = on_message
    
    try:
        # Removed clean_start to fix the error you saw
        c.connect(B, 8883, keepalive=60)
        c.loop_start()
        return c
    except Exception as e:
        st.session_state.status = f"⚠️ Connection Error: {str(e)}"
        return None




















get_mqtt()

# --- 5. UI ---
st.title("🏭 Factory Monitor")
st.subheader(f"System Status: {st.session_state.status}")

if st.session_state.data:
    cols = st.columns(len(st.session_state.data))
    for i, (k, v) in enumerate(st.session_state.data.items()):
        cols[i].metric(label=k.upper(), value=v)
else:
    st.info("Waiting for data... Please trigger Node-RED.")

time.sleep(2)
st.rerun()
