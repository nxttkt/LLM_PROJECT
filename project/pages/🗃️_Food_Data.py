import streamlit as st
import requests
import os
from dotenv import load_dotenv

# โหลดไฟล์ .env
load_dotenv()

# ใช้ค่า API key จาก .env
openai_api_key = os.getenv("OPENAI_API_KEY")
usda_api_key = os.getenv("USDA_API_KEY")

# ฟังก์ชันค้นหาข้อมูลอาหารจาก USDA API
def get_food_data(food_item):
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_item}&api_key={usda_api_key}"
    response = requests.get(url)
    data = response.json()
    return data['foods'][0] if data['foods'] else None

# RAG
def rag_chatbot(query):
    # Retrieval: ดึงข้อมูลอาหารจาก USDA API
    food_info = get_food_data(query)
    
    if food_info:
        # ข้อมูลอาหารจาก USDA
        food_name = food_info['description']
        calories = food_info['foodNutrients'][0]['value']  # แคลอรี่
        protein = food_info['foodNutrients'][1]['value']   # โปรตีน
        carbs = food_info['foodNutrients'][2]['value']     # คาร์โบไฮเดรต
        fat = food_info['foodNutrients'][3]['value']       # ไขมัน
        
        # สร้างคำตอบจากข้อมูลที่ได้
        response = f"ข้อมูลของ {food_name}:\n- แคลอรี่: {calories} kcal\n- โปรตีน: {protein} g\n- คาร์โบไฮเดรต: {carbs} g\n- ไขมัน: {fat} g"
    else:
        # หากไม่พบข้อมูล
        response = "I Don't know what it is, please try again!"
    
    return response

# Streamlit UI
st.title("Food Data From USDA API")

query = st.text_input("Please write the food name in English only. (Pizza, Burger, Milk, etc.)")
if query:
    answer = rag_chatbot(query)
    st.write(answer)
