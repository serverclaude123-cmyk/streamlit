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
