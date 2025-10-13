import os
import io
import requests
from dotenv import load_dotenv
import streamlit as st

# โหลดค่าตัวแปรจากไฟล์ .env
load_dotenv()

st.set_page_config(page_title="This content is not yet available.", page_icon="🍽️")

st.title("Image detection with LogMeal")
st.caption("This content is not yet available.")


# CAMERA
st.subheader("TITAN CAMERAMAN")
enable = st.checkbox("Enable camera")
picture = st.camera_input("Take a picture", disabled=not enable)

# UPLOAD
st.subheader("Upload File")
uploaded = st.file_uploader("Support for .jpg .jpeg .png", type=["jpg", "jpeg", "png"])

# CHOOSE A FILE
img_file = picture or uploaded
if img_file:
    st.image(img_file, caption="ภาพที่เลือก", use_container_width=True)


st.markdown("---")
go = st.button("Results")

st.sidebar.title("This content is not yet available.")
