import os
import io
import requests
from dotenv import load_dotenv
import streamlit as st

# โหลดค่าตัวแปรจากไฟล์ .env
load_dotenv()

st.set_page_config(page_title="Food Guess (LogMeal)", page_icon="🍽️")

st.title("🍽️ เดาเมนูอาหารจากภาพ (LogMeal)")
st.caption("อัปโหลดหรือถ่ายภาพ → ส่งไปยัง LogMeal API → รับผลลัพธ์เป็นชื่อเมนู + ความมั่นใจ")

# ----- ใส่ API Key -----
LM_TOKEN = os.getenv("LOGMEAL_TOKEN")

if not LM_TOKEN:
    st.warning("ไม่ได้ตั้งค่า LOGMEAL_TOKEN ในไฟล์ .env")

# ----- กล้อง -----
st.subheader("กล้องถ่ายรูป")
enable = st.checkbox("Enable camera")
picture = st.camera_input("Take a picture", disabled=not enable)

# ----- อัปโหลด -----
st.subheader("อัปโหลดรูปภาพ")
uploaded = st.file_uploader("รองรับ .jpg .jpeg .png", type=["jpg", "jpeg", "png"])

# ----- เลือกแหล่งภาพ (ให้กล้องมาก่อน) -----
img_file = picture or uploaded
if img_file:
    st.image(img_file, caption="ภาพที่เลือก", use_container_width=True)


st.markdown("---")
top_k = st.slider("จำนวนตัวเลือกที่อยากเห็น (top_k)", 1, 5, 3)
go = st.button("🔍 วิเคราะห์ด้วย LogMeal")

# ====== ฟังก์ชันเรียก LogMeal ======
def logmeal_classify(image_bytes: bytes, token: str, top_k: int = 3):
    """
    เรียก LogMeal dish classification (ตัวอย่าง endpoint รุ่น v2)
    เอกสารจริงอาจใช้ path แตกต่างตามแผน — เช็กใน docs ของคุณอีกที
    """
    url = f"https://api.logmeal.com/v2/recognition/dish/classify?top_k={top_k}"
    headers = {"Authorization": f"Bearer {token}"}
    files = {"image": ("image.jpg", image_bytes, "image/jpeg")}
    # หมายเหตุ: ต้องส่งแบบ multipart/form-data ตามที่ LogMeal แนะนำ
    # (ดูหน้าคู่มือ/ทิวโทเรียลของ LogMeal)  
    resp = requests.post(url, headers=headers, files=files, timeout=30)
    resp.raise_for_status()
    return resp.json()

if go:
    if not img_file:
        st.warning("กรุณาเลือกภาพจากกล้องหรืออัปโหลดไฟล์ก่อนนะ")
    elif not LM_TOKEN:
        st.error("ยังไม่มี LogMeal API Token (Bearer) — ใส่ใน .env หรือเซ็ตตัวแปร ENV `LOGMEAL_TOKEN`")
    else:
        with st.spinner("กำลังส่งภาพไปยัง LogMeal ..."):
            try:
                # ดึง bytes ของภาพ (รองรับทั้ง camera_input และ file_uploader)
                img_bytes = img_file.getvalue() if hasattr(img_file, "getvalue") else img_file.read()
                data = logmeal_classify(img_bytes, LM_TOKEN, top_k=top_k)

                st.subheader("ผลลัพธ์จาก LogMeal")
                # โครงสร้างผลลัพธ์จริงอาจต่างกันเล็กน้อยตาม tier/รุ่น API
                # ส่วนใหญ่จะมีรายการ "predictions" หรือ "recognition_results"
                # ใส่ fallback ให้ยืดหยุ่น
                preds = (
                    data.get("recognition_results")
                    or data.get("predictions")
                    or data.get("dishes")
                    or []
                )

                if not preds:
                    st.info(f"ไม่พบผลลัพธ์ที่จำแนกได้\n\nraw: `{data}`")
                else:
                    for i, p in enumerate(preds, 1):
                        # ฟิลด์ที่พบบ่อย: name/label + probability/prob/score + (id)
                        name = p.get("name") or p.get("label") or p.get("dish") or "Unknown"
                        prob = p.get("probability") or p.get("prob") or p.get("score")
                        dish_id = p.get("id") or p.get("class_id")
                        col1, col2, col3 = st.columns([3,2,2])
                        with col1:
                            st.markdown(f"**#{i}. {name}**")
                        with col2:
                            if prob is not None:
                                st.write(f"ความมั่นใจ: {float(prob):.2f}")
                            else:
                                st.write("ความมั่นใจ: -")
                        with col3:
                            st.write(f"Dish ID: {dish_id or '-'}")

                with st.expander("ดู raw JSON"):
                    st.code(data, language="json")

            except requests.HTTPError as e:
                st.error(f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                st.exception(e)
