import streamlit as st

st.title("Try to take a picture with Camera")

st.write("TRY DI WA")

enable = st.checkbox("Enable camera")
picture = st.camera_input("Take a picture", disabled=not enable)

if picture:
    st.image(picture)