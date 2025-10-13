from dotenv import load_dotenv
load_dotenv()

import os
import re
import requests
import streamlit as st
from openai import OpenAI

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL   = st.secrets.get("MODEL")  # ใช้ค่าจาก secrets; ถ้าไม่ตั้งจะ fallback ข้างล่าง
USDA_API_KEY = st.secrets.get("USDA_API_KEY") or os.getenv("USDA_API_KEY")

st.set_page_config(
    page_title="CALORE BOT",
    page_icon="🤖",
)

# ---------------------------------------------------
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
# ---------------------------------------------------

# ------------- USDA RAG -------------
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

    client = OpenAI(api_key=API_KEY)
    resp = client.chat.completions.create(
        model=MODEL or "gpt-4o-mini",
        messages=messages,
        temperature=0,
        top_p=1,
        presence_penalty=0,
        frequency_penalty=0,
    )
    return resp.choices[0].message.content.strip()
# --------- /USDA RAG ---------

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
    """ตรวจจับชื่ออาหารจากข้อความผู้ใช้"""
    if not text or not isinstance(text, str):  # ✅ กัน text เป็น None หรือ type อื่น
        return None
    t = text.lower().strip()

    for th, en in THAI_FOOD_MAP.items():
        if th in t:
            return en  # คืนชื่ออังกฤษเพื่อใช้ค้นใน USDA

    for w in FOOD_WORDS:
        if w in t:
            return w

    m = re.search(r"(fried rice|green curry|tom yum|pad thai|hainanese chicken rice)", t)
    if m:
        return m.group(1)
    return None

FOLLOWUP_HINTS = [
    "แล้ว", "ต่อ", "อีก", "เท่าไหร่", "กี่แคล", "โปรตีน", "ไขมัน", "คาร์บ",
    "sugar", "fiber", "sodium"
]

def is_followup(text: str) -> bool:
    t = text.strip().lower()
    return (detect_food_from_text(t) is None) and any(w in t for w in FOLLOWUP_HINTS)

# ---------- LLM Client Wrapper (รองรับ SDK v1) ----------
class LLMClient:
    def __init__(self, api_key: str, model_name: str | None):
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name or "gpt-4o-mini"

    def chat(self, messages, temperature=0, top_p=1, presence_penalty=0, frequency_penalty=0):
        # คง BOT_PROMPT เดิมไว้เป็น system message แรก
        final_messages = [{"role": "system", "content": BOT_PROMPT}]
        final_messages.extend(messages)

        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=final_messages,
            temperature=temperature,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
        )
        return resp.choices[0].message.content.strip()

# ---------- Session State ----------
def init_session_state():
    if "last_food" not in st.session_state:
        st.session_state.last_food = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "llm_client" not in st.session_state:
        try:
            st.session_state.llm_client = LLMClient(API_KEY, MODEL)
        except Exception:
            # Fallback: ไม่ให้แอปพังแม้ไม่มีคีย์
            class EchoClient:
                def chat(self, messages, **kwargs):
                    if not messages:
                        return "(no messages)"
                    last = messages[-1].get("content", "")
                    return "(LLM unavailable) I would respond to: '" + last + "'"
            st.session_state.llm_client = EchoClient()

def display_chat_messages():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ---------- UI ----------
init_session_state()

st.title("CALORE Bot")
st.write("Type a message to talk with Calore Bot!")

# แสดงประวัติแชท
display_chat_messages()

# รับข้อความผู้ใช้
if prompt := st.chat_input("Type your message here..."):
    # เก็บข้อความผู้ใช้
    st.session_state.messages.append({"role": "user", "content": prompt})

    # ตรวจจับชื่ออาหารและจำล่าสุด
    food_in_msg = detect_food_from_text(prompt)
    if food_in_msg:
        st.session_state.last_food = food_in_msg

    with st.chat_message("user"):
        st.markdown(prompt)

    # ตอบกลับ
with st.chat_message("assistant"):
    with st.spinner("Thinking..."):
        query_food = detect_food_from_text(prompt)

        # ถ้าไม่เจออาหารใหม่ แต่เป็นคำถามต่อเนื่อง → ใช้อาหารล่าสุด
        if not query_food and is_followup(prompt) and st.session_state.last_food:
            query_food = st.session_state.last_food

        response_text = None

        if query_food:
            st.session_state.last_food = query_food
            response_text = rag_chatbot(prompt, query_food)

            # ถ้า RAG ไม่เจอข้อมูลเลย → ให้โมเดลหลักตอบแทน
            if response_text is None:
                response_text = st.session_state.llm_client.chat(
                    [{"role": "user", "content": prompt}],
                    temperature=0,
                    top_p=1,
                    presence_penalty=0,
                    frequency_penalty=0,
                )
        else:
            # ❗️ไม่ใช่อาหาร → ให้ขอโทษและถามข้อมูลเพิ่มโดยตรง
            response_text = (
                "ขอโทษนะครับ/ค่ะ ตอนนี้ยังระบุชื่ออาหารไม่ได้ "
                "ช่วยบอกชื่อเมนูให้ชัดเจนหน่อยได้ไหมครับ/คะ "
                "เช่น “ผัดไทย 1 จาน” หรือ “อกไก่ย่าง 150 กรัม”?"
            )

        st.markdown(response_text)

    # เก็บคำตอบบอท
    st.session_state.messages.append({"role": "assistant", "content": response_text})

# ------------- SIDE BAR -------------
st.sidebar.title("What is Calore Bot?")
st.sidebar.text(
    "Calore Bot is a chatbot that can tell you how healthy the food you're "
    "looking for is, whether it's protein, calories, or the main ingredients of the food."
)

# ------------- FeedBack -------------
with st.sidebar:
    sentiment_mapping = ["one", "two", "three", "four", "five"]
    selected = st.feedback("stars")
    if selected is not None:
        st.markdown(
            f"You selected {sentiment_mapping[selected]} star(s). Thank you for feedback!"
        )


