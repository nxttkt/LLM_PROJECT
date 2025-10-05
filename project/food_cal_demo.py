import streamlit as st
import pandas as pd
import numpy as np

# TAB BAR
st.set_page_config(
    page_title="Calories Calculator",
    page_icon="🍕",
) 

# TITLE
st.title('Calories Calculator')

# TOPIC
st.write("# Hello, Welcome 👋")

# SIDEBAR ON THE LEFT
st.sidebar.success("⬆️Select mode from above⬆️")

# DESCRIPTION
st.markdown(
    """
    ### Want to know what this dish is? You can take a pictures!.
    - Jump into [Webcam](http://localhost:8501/Webcam_demo)
    ### What? Are you not comfortable taking photos? Ask our chatbot!
    - Check out [Here](http://localhost:8502/chat_bot)
"""
)
