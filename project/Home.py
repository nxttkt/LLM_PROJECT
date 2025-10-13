import streamlit as st
import pandas as pd
import numpy as np
from streamlit_option_menu import option_menu

# TAB BAR
st.set_page_config(
    page_title="Hello, Welcome",
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
    st.title('Calore FoodChat')
    st.write("### Want to know how healthy the food you're eating is? Talk to Calore!")
    st.markdown("--------------")
    

if selected == "About":
    st.title("About us")
    st.write("### We created this application to learn how to use Streamlit and develop programs with LLM.")
    st.markdown("--------------")

if selected == "Members":
    st.title("Members list")
    st.markdown("""
        - 670510701 ชยางกูร นาคำ
        - 670510704 ณัฏฐกิตติ์ แสนมงคล
        - 670510712 นวคุณ วรรณขัน
        - 670510722 เมธานันท์ ลาดี
        """)



# SIDEBAR
st.sidebar.title("About us")
st.sidebar.text("We created this application to learn how to use Streamlit and develop programs with LLM.")

# ใส่ข้อความใน Sidebar
st.sidebar.title("BMI Calculator")
# กล่องรับค่าน้ำหนักและส่วนสูง
weight = st.sidebar.number_input("Weight (kg):", min_value=0.0, step=0.1)
height = st.sidebar.number_input("Height (cm):", min_value=0.0, step=0.1)

# ปุ่มให้ผู้ใช้กดคำนวณ
if st.sidebar.button("Calculate BMI"):
    if height > 0:
        # Convert height from cm to meters
        height_m = height / 100
        bmi = weight / (height_m ** 2)

        # Interpret BMI result
        if bmi < 18.5:
            result = "Underweight"
        elif bmi < 23:
            result = "Normal weight"
        elif bmi < 25:
            result = "Overweight"
        elif bmi < 30:
            result = "Obese (Level 1)"
        else:
            result = "Obese (Level 2)"

        # Display results
        st.subheader("BMI Calculation Result")
        st.write(f"**Your BMI:** {bmi:.2f}")
        st.write(f"**Category:** {result}")
    else:
        st.warning("Please enter a valid height before calculating.")
