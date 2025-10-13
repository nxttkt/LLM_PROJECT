from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
import sys
import requests
import re

# ✅ ใช้ OpenAI SDK v1
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL")
USDA_API_KEY = os.getenv("USDA_API_KEY")

st.set_page_config(
    page_title="CALORE BOT",
    page_icon="🤖",
)

BOT_PROMPT = (
    "You are CALORE Bot. Respond in Thai with a detailed, structured nutrition report. "
    "If USDA/retrieval data is available, use it. If not, provide a clearly-labeled ESTIMATE "
    "based on common recipes WITHOUT asking follow-ups or apologizing. Include:\n"
    "1) พลังงานต่อ 100 กรัม และต่อ 1 ที่เสิร์ฟ (ช่วงค่าประมาณ)\n"
    "2) โปรตีน ไขมัน คาร์บ (และถ้าคาดได้ ใส่ น้ำตาล ใยอาหาร โซเดียม)\n"
    "3) หมายเหตุสมมติฐานสูตรทั่วไป (เช่น ข้าว ~180–200 g, น้ำมัน ~1 ช้อนโต๊ะ)\n"
    "4) คำแนะนำย่อเพื่อปรับแคลอรี่/สุขภาพ\n"
    "Keep it factual and organized with bullet points."
)

# ----------------------------- RAG ---------------------------------
def get_food_data(food_item):
    if not USDA_API_KEY:
        return None

    queries = food_item if isinstance(food_item, list) else [food_item]
    for q in queries:
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={q}&api_key={USDA_API_KEY}"
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            if not data.get("foods"):
                continue

            first = data["foods"][0]
            desc = (first.get("description") or "").lower()

            # ต้องมี token ของคำค้นอย่างน้อย 1 ตัวในชื่อ
            tokens = [t for t in q.lower().split() if t.isalpha()]
            if tokens and not any(tok in desc for tok in tokens):
                continue

            return first
        except Exception:
            continue
    return None  # fallback ไป OpenAI


def rag_chatbot(query, food_name=None):
    # ใช้ OpenAI SDK v1
    client = OpenAI(api_key=API_KEY)

    food_info = get_food_data(food_name or query)
    if not food_info:
        return None   # ให้ตัวเรียกไปใช้ OpenAI ต่อ

    name = food_info.get("description", "N/A")
    nutrients = food_info.get("foodNutrients", [])

    def pick(nnum):
        for n in nutrients:
            if str(n.get("nutrientNumber")) == nnum:
                return n.get("value")
        return None

    cal  = pick("208"); protein = pick("203"); fat = pick("204"); carb = pick("205")

    # ตอบสั้น/ยาวตามที่คุณตั้ง แต่ระบุแหล่งที่มาให้ชัด
    context = (
        f"Name: {name}\n"
        f"Calories: {cal} kcal per 100g\n"
        f"Protein: {protein} g\n"
        f"Fat: {fat} g\n"
        f"Carbohydrate: {carb} g\n"
    )

    # ตรวจภาษาอย่างง่ายจาก query
    is_english = bool(re.search(r"[A-Za-z]", query))
    lang = "English" if is_english else "Thai"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a nutrition assistant. Use only the given CONTEXT. "
                "Answer briefly with numeric facts in the requested language "
                "(per 100 g, per serving if present)."
            ),
        },
        {
            "role": "user",
            "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}\nAnswer in {lang}.",
        },
    ]

    resp = client.chat.completions.create(
        model=MODEL or "gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        top_p=1,
        presence_penalty=0,
        frequency_penalty=0,
    )
    return resp.choices[0].message.content.strip()
# --------------------------- /RAG ----------------------------------


# อาหารไทยเป็นอังกฤษ (บางส่วน)
THAI_FOOD_MAP = {
    "ข้าวผัด": "fried rice",
    "ผัดไทย": "pad thai",
}

# รายการคำอาหารที่รู้จัก (อังกฤษ)
FOOD_WORDS = [
    "fried rice", "rice", "chicken", "pork", "egg", "noodle", "soup", "curry",
    "green curry", "pad thai", "hainanese chicken rice", "spaghetti",
]

def detect_food_from_text(text: str) -> str | None:
    """ตรวจจับชื่ออาหารจากข้อความผู้ใช้ (กัน None/ชนิดอื่นไว้ด้วย)"""
    if not text or not isinstance(text, str):
        return None

    t = text.lower().strip()

    # ลองจับชื่ออาหารไทยดูก่อน
    for th, en in THAI_FOOD_MAP.items():
        if th in t:
            return en  # คืนชื่ออังกฤษเพื่อใช้ค้นใน USDA

    # ให้ลองจับคำอังกฤษที่รู้จัก
    for w in FOOD_WORDS:
        if w in t:
            return w

    # ลอง regex ดู (อาจจับคำยาวๆ ได้)
    m = re.search(r"(fried rice|green curry|tom yum|pad thai|hainanese chicken rice)", t)
    if m:
        return m.group(1)

    # ไม่เจอ
    return None

FOLLOWUP_HINTS = [
    "แล้ว", "ต่อ", "อีก", "เท่าไหร่", "กี่แคล", "โปรตีน", "ไขมัน", "คาร์บ",
    "sugar", "fiber", "sodium"
]

def is_followup(text: str) -> bool:
    t = (text or "").strip().lower()
    return (detect_food_from_text(t) is None) and any(w in t for w in FOLLOWUP_HINTS)


def init_session_state():
    """Initialize session state variables"""
    if "last_food" not in st.session_state:
        st.session_state.last_food = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "llm_client" not in st.session_state:
        # Create a safe llm_client: try OpenAI if available and configured,
        # otherwise provide a lightweight fallback that avoids AttributeError.
        def create_llm_client():
            try:
                if not API_KEY:
                    raise RuntimeError("OPENAI_API_KEY not set")

                model_name = MODEL or "gpt-3.5-turbo"

                class OpenAIClient:
                    def __init__(self, api_key, model):
                        # ✅ ใช้ SDK v1
                        self.client = OpenAI(api_key=api_key)
                        self.model = model

                    def chat(self, messages):
                        final_messages = [{"role": "system", "content": BOT_PROMPT}]
                        final_messages.extend(messages)

                        resp = self.client.chat.completions.create(
                            model=self.model,
                            messages=final_messages,
                            temperature=0,
                            top_p=1,
                            presence_penalty=0,
                            frequency_penalty=0,
                        )
                        return resp.choices[0].message.content.strip()

                return OpenAIClient(API_KEY, model_name)
            except Exception:
                # Fallback: a minimal client that echoes the last user message
                class EchoClient:
                    def chat(self, messages):
                        if not messages:
                            return "(no messages)"
                        last = messages[-1].get("content", "")
                        return "(LLM unavailable) I would respond to: '" + last + "'"

                return EchoClient()

        st.session_state.llm_client = create_llm_client()

def display_chat_messages():
    """Display chat messages"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


init_session_state()

st.title("CALORE Bot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # ตรวจจับชื่ออาหารจากข้อความ และจำไว้ใน session
    food_in_msg = detect_food_from_text(prompt)
    if food_in_msg:
        st.session_state.last_food = food_in_msg

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # ใช้ชื่ออาหารล่าสุดถ้าไม่มีในข้อความนี้
            query_food = detect_food_from_text(prompt)
            if query_food:
                st.session_state.last_food = query_food
            elif is_followup(prompt) and st.session_state.last_food:
                query_food = st.session_state.last_food
            else:
                query_food = None

            # เรียก RAG ถ้ามีชื่ออาหารให้ค้น
            response = None
            if query_food:
                response = rag_chatbot(prompt, query_food)

            # ถ้าไม่ใช่อาหาร (และไม่ใช่ follow-up ที่พอระบุได้) → ขอโทษและขอข้อมูลเพิ่ม
            if response is None and query_food is None:
                response = (
                    "ขอโทษนะครับ/ค่ะ ตอนนี้ยังระบุชื่ออาหารไม่ได้ "
                    "ช่วยบอกชื่อเมนูให้ชัดเจนหน่อยได้ไหมครับ/คะ "
                    "เช่น “ผัดไทย 1 จาน” หรือ “อกไก่ย่าง 150 กรัม”?"
                )

            # ถ้าเป็นอาหารแต่ RAG ไม่เจอ → ให้โมเดลหลักตอบตาม BOT_PROMPT
            if response is None and query_food is not None:
                response = st.session_state.llm_client.chat(
                    [{"role": "user", "content": prompt}]
                )

            # แสดงผล
            st.markdown(response)

    # บันทึกคำตอบของบอท
    st.session_state.messages.append({"role": "assistant", "content": response})
