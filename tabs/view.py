# -*- coding: utf-8 -*-
"""
Tab View - Xem và xóa Test
"""
import streamlit as st
from storage import save_question_bank


def render_view_tab(tab):
    """Render tab xem và xóa Test"""
    with tab:
        st.header("3️⃣ Xem lại Test đã upload / Xóa Test")

        available_tests = sorted(
            {q["test_id"] for group in st.session_state.question_bank.values() for q in group}
        )

        if not available_tests:
            st.write("Chưa có Test nào trong ngân hàng.")
        else:
            selected_test = st.selectbox(
                "Chọn Test để xem chi tiết:",
                options=available_tests,
                format_func=lambda x: f"Test {int(x)}",
                key="view_test_select",
            )

            if st.button(f"🗑️ XÓA toàn bộ dữ liệu của Test {selected_test}", key="delete_test_button"):
                for g in [1, 2, 3, 4]:
                    st.session_state.question_bank[g] = [
                        q for q in st.session_state.question_bank[g] if q["test_id"] != selected_test
                    ]
                # Tự động lưu sau khi xóa
                save_question_bank(st.session_state.question_bank)
                st.success(f"Đã xóa và lưu dữ liệu của Test {selected_test}! 💾")
                st.rerun()

            # Cập nhật lại danh sách
            available_tests = sorted(
                {q["test_id"] for group in st.session_state.question_bank.values() for q in group}
            )

            if available_tests and selected_test in {
                q["test_id"] for group in st.session_state.question_bank.values() for q in group
            }:
                per_group = {g: 0 for g in [1, 2, 3, 4]}
                for g in [1, 2, 3, 4]:
                    per_group[g] = sum(
                        1 for q in st.session_state.question_bank[g] if q["test_id"] == selected_test
                    )

                st.markdown(
                    f"""
**Tổng quan Test {selected_test}:**

- Nhóm 1 (Q1–13): {per_group[1]} câu  
- Nhóm 2 (Q14): {per_group[2]} câu  
- Nhóm 3 (Q15): {per_group[3]} block  
- Nhóm 4 (Q16–17): {per_group[4]} block  
"""
                )

                for g in [1, 2, 3, 4]:
                    st.subheader(f"Nhóm {g} của Test {selected_test}")
                    questions = [
                        q for q in st.session_state.question_bank[g] if q["test_id"] == selected_test
                    ]
                    questions.sort(key=lambda x: x["index_in_test"])

                    if not questions:
                        st.write("❌ Chưa có câu nào của nhóm này.")
                        continue

                    for q in questions:
                        st.markdown(
                            f"**Question {q['index_in_test']} (Nhóm {q['group']} – kiểu {q['type']})**"
                        )
                        if q["type"] == "mcq":
                            st.text(q["stem"])
                            for lbl, txt in q["options"].items():
                                st.write(f"{lbl}. {txt}")
                            st.write(f"_Answer: {q['answer']}_")
                        elif q["type"] == "mcq_multi":
                            if q["intro"]:
                                st.text(q["intro"])
                            for j, item in enumerate(q["items"], start=1):
                                st.write(f"{j}. {item['stem']}")
                                for lbl, txt in item["options"].items():
                                    st.write(f"   {lbl}. {txt}")
                                st.write(f"   Answer: {item['answer']}")
                        elif q["type"] == "order":
                            st.text(q["prompt"])
                            for j, item in enumerate(q["items"], start=1):
                                st.write(f"{j}. {item}")
                        elif q["type"] == "gender_block":
                            for item in q["items"]:
                                st.write(f"- {item['stem']}  →  {item['gender']}")
                        st.markdown("---")
