import certifi # Add this at the top of your file

@st.cache_resource
def get_client():
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(U, P)
    
    # Use certifi to find the correct certificates for a secure connection
    c.tls_set(ca_certs=certifi.where()) 
    
    c.on_connect = on_connect
    c.on_message = on_message
    
    # Increase timeout to 60 seconds
    try:
        c.connect(B, 8883, keepalive=60)
        c.subscribe("hive/a")
        c.loop_start()
    except Exception as e:
        st.session_state.status = f"❌ Connection Error: {e}"
        
    return c
