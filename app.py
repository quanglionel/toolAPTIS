# -*- coding: utf-8 -*-
"""
Tool luyện đề APTIS - Entry Point
Ứng dụng Streamlit để luyện đề thi APTIS với 17 câu hỏi
"""
import streamlit as st

# Import các tab
from tabs import (
    render_info_tab,
    render_upload_tab,
    render_stats_tab,
    render_view_tab,
    render_exam_tab,
)
from storage import load_question_bank


# ==========================
#  CẤU HÌNH TRANG
# ==========================

st.set_page_config(page_title="Tool luyện đề từ nhiều Test", layout="wide")

# ---- CSS cho responsive & giao diện gọn gàng ----
CUSTOM_CSS = """
<style>
/* Giới hạn độ rộng nội dung, căn giữa */
.main .block-container {
    max-width: 1100px;
    padding-top: 1rem;
    padding-bottom: 3rem;
}

/* Tiêu đề gọn hơn một chút */
h1, h2, h3 {
    margin-top: 0.6rem;
    margin-bottom: 0.4rem;
}

/* Canh giữa thanh tab + khoảng cách đều nhau */
.stTabs [role="tablist"] {
    justify-content: center;   /* căn giữa các tab */
    gap: 1rem;                 /* khoảng cách giữa các tab */
}

/* Style cho từng tab */
.stTabs [role="tab"] {
    font-weight: 600;
    padding: 0.3rem 0.8rem;
    border-radius: 999px;      /* bo tròn nhìn như pill */
}

/* Responsive cho màn hình nhỏ (tablet, mobile) */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }

    /* Cho phép tab xuống hàng và vẫn căn giữa */
    .stTabs [role="tablist"] {
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.5rem;
    }

    /* Các input chiếm full width */
    input[type="number"],
    .stTextInput input,
    .stFileUploader,
    .stRadio > div,
    .stSelectbox > div,
    .stMultiSelect > div {
        width: 100% !important;
    }
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==========================
#  SESSION STATE
# ==========================

if "question_bank" not in st.session_state:
    # Tự động tải dữ liệu đã lưu (nếu có)
    st.session_state.question_bank = load_question_bank()

if "current_exam" not in st.session_state:
    st.session_state.current_exam = []


# ==========================
#  MAIN UI
# ==========================

st.title("📚 Tool luyện đề từ nhiều Test (17 câu cố định thứ tự)")

# Tạo các tab
tab_info, tab_upload, tab_stats, tab_view, tab_exam = st.tabs(
    [
        "ℹ️ Information",
        "1️⃣ Upload Test",
        "2️⃣ Thống kê ngân hàng",
        "3️⃣ Xem / Xóa Test",
        "4️⃣ Tạo đề & Luyện tập",
    ]
)

# Tính counts cho các tab cần dùng
counts = {g: len(st.session_state.question_bank[g]) for g in [1, 2, 3, 4]}

# Render các tab
render_info_tab(tab_info)
render_upload_tab(tab_upload)
render_stats_tab(tab_stats, counts)
render_view_tab(tab_view)
render_exam_tab(tab_exam, counts)
