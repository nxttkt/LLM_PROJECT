import streamlit as st
import pandas as pd
import numpy as np
from streamlit_option_menu import option_menu

# TAB BAR
st.set_page_config(
    page_title="FOOD DATA",
    page_icon="🍕",
) 


# horizontal menu
selected = option_menu(
    menu_title=None,
    options=["Home", "About", "Members"],
    icons=["house", "bezier", "people-fill"],
    default_index=0,
    orientation="horizontal"
)


# menu title selected
if selected == "Home":
    st.title('Calore Food Bot')
    st.write("### Want to know how beneficial the food you're eating is? Talk to Calore!")
    st.link_button("Get Started", "http://localhost:8501/Calore_Bot")
    st.markdown("--------------")
    

if selected == "About":
    st.title("About us")
    st.write("### We created this application to learn how to use Streamlit and develop programs with LLM.")
    st.markdown("--------------")


# SIDEBAR ON THE LEFT
st.sidebar.success("⬆️SELECT PAGES⬆️")

# SIDEBAR
st.sidebar.title("About us")
st.sidebar.text("We created this application to learn how to use Streamlit and develop programs with LLM.")
