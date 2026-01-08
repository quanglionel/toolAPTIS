# -*- coding: utf-8 -*-
"""
Tab Exam - Tạo đề và luyện tập
"""
import random
import streamlit as st


def render_exam_tab(tab, counts=None):
    """Render tab tạo đề và luyện tập"""
    with tab:
        st.header("4️⃣ Tạo đề & Luyện tập")

        # Luôn tính counts trực tiếp từ session_state để đảm bảo dữ liệu mới nhất
        current_counts = {g: len(st.session_state.question_bank[g]) for g in [1, 2, 3, 4]}

        can_generate = (
            current_counts[1] >= 13
            and current_counts[2] >= 1
            and current_counts[3] >= 1
            and current_counts[4] >= 2
        )

        if not can_generate:
            st.warning(
                "⚠ Chưa đủ câu để tạo đề 17 câu.\n"
                "- Cần ≥13 câu Nhóm 1\n"
                "- ≥1 câu Nhóm 2\n"
                "- ≥1 block Nhóm 3\n"
                "- ≥2 block Nhóm 4"
            )
        else:
            if st.button("🎲 Tạo đề 17 câu (giữ thứ tự 1–17)", key="create_exam_button"):
                q1 = random.sample(st.session_state.question_bank[1], 13)
                q2 = random.choice(st.session_state.question_bank[2])
                q3 = random.choice(st.session_state.question_bank[3])
                q4 = random.sample(st.session_state.question_bank[4], 2)

                exam_questions = []
                exam_questions.extend(q1)      # Câu 1–13
                exam_questions.append(q2)      # Câu 14
                exam_questions.append(q3)      # Câu 15
                exam_questions.extend(q4)      # Câu 16–17

                # Chuẩn bị dữ liệu shuffle cho câu sắp xếp
                for q in exam_questions:
                    if q["type"] == "order":
                        q["shuffled_items"] = random.sample(q["items"], len(q["items"]))

                st.session_state.current_exam = exam_questions
                st.success("✅ Đã tạo đề. Kéo xuống để làm bài.")

        # --------- LÀM ĐỀ & CHẤM ---------
        if st.session_state.current_exam:
            st.subheader("📄 Đề luyện tập & chấm điểm")

            score_mcq = 0
            total_mcq = 0

            score_order = 0
            total_order = 0

            score_gender = 0
            total_gender = 0

            for i, q in enumerate(st.session_state.current_exam):
                st.markdown(
                    f"### Câu {i+1} (Test {q['test_id']} – Question {q['index_in_test']} – Nhóm {q['group']})"
                )

                # --- Nhóm 1 & MCQ đơn trong Nhóm 4 ---
                if q["type"] == "mcq":
                    st.text(q["stem"])
                    option_labels = sorted(q["options"].keys())
                    option_entries = [f"{lbl}. {q['options'][lbl]}" for lbl in option_labels]

                    chosen = st.radio(
                        "Chọn đáp án:",
                        options=option_entries,
                        index=None,
                        key=f"mcq_{i}",
                    )

                    total_mcq += 1

                    if chosen is not None:
                        chosen_label = chosen.split(".", 1)[0].strip().upper()
                        if chosen_label == q["answer"]:
                            st.success(f"✅ Đúng (Answer: {q['answer']})")
                            score_mcq += 1
                        else:
                            st.error(f"❌ Sai. Answer đúng là: {q['answer']}")

                # --- Nhóm 4: MCQ nhiều câu con ---
                elif q["type"] == "mcq_multi":
                    if q["intro"]:
                        st.text(q["intro"])

                    for j, item in enumerate(q["items"], start=1):
                        st.write(f"**Câu {j}: {item['stem']}**")
                        opt_labels = sorted(item["options"].keys())
                        opt_entries = [
                            f"{lbl}. {item['options'][lbl]}" for lbl in opt_labels
                        ]
                        chosen = st.radio(
                            "",
                            options=opt_entries,
                            index=None,
                            key=f"mcq_multi_{i}_{j}",
                        )

                        total_mcq += 1

                        if chosen is not None:
                            chosen_label = chosen.split(".", 1)[0].strip().upper()
                            if chosen_label == item["answer"]:
                                st.success(f"✅ Đúng (Answer: {item['answer']})")
                                score_mcq += 1
                            else:
                                st.error(f"❌ Sai. Answer đúng là: {item['answer']}")

                # --- Nhóm 2: ORDER ---
                elif q["type"] == "order":
                    st.text(q["prompt"])
                    items_correct = q["items"]
                    items_shuffled = q.get("shuffled_items", items_correct)

                    st.write("Các mục (thứ tự NGẪU NHIÊN):")
                    for idx_item, item in enumerate(items_shuffled, start=1):
                        st.write(f"{idx_item}. {item}")

                    st.write("➡ Hãy chọn lại tất cả mục theo **thứ tự ĐÚNG**:")

                    selected = st.multiselect(
                        "Chọn lần lượt từ mục đầu đến cuối:",
                        options=items_shuffled,
                        key=f"order_{i}",
                    )

                    total_order += 1

                    if len(selected) == len(items_correct):
                        if selected == items_correct:
                            st.success("✅ Thứ tự hoàn toàn đúng!")
                            score_order += 1
                        else:
                            st.error("❌ Thứ tự chưa đúng.")
                            with st.expander("Xem thứ tự đúng"):
                                for idx_item, item in enumerate(items_correct, start=1):
                                    st.write(f"{idx_item}. {item}")
                    else:
                        st.info("Chọn đủ tất cả các mục theo thứ tự bạn nghĩ là đúng để kiểm tra.")

                # --- Nhóm 3: GENDER BLOCK ---
                elif q["type"] == "gender_block":
                    st.write("Chọn người nói (woman / man / both) cho từng câu:")

                    for j, item in enumerate(q["items"], start=1):
                        st.write(f"- {item['stem']}")
                        choice = st.selectbox(
                            "Người nói:",
                            options=["woman", "man", "both"],
                            index=None,
                            placeholder="Chọn...",
                            key=f"gender_{i}_{j}",
                        )
                        total_gender += 1
                        if choice is not None:
                            if choice.lower() == item["gender"]:
                                st.success("✅ Đúng")
                                score_gender += 1
                            else:
                                st.error(f"❌ Sai. Đáp án: {item['gender']}")

                st.markdown("---")

            # --------- TỔNG KẾT ---------
            st.subheader("🧮 Tổng kết")

            st.write("### Kết quả theo nhóm:")

            st.write(f"- **Trắc nghiệm (Nhóm 1 & 4)**: {score_mcq} / {total_mcq} câu con đúng")
            st.write(f"- **Câu sắp xếp (Nhóm 2)**: {score_order} / {total_order} câu đúng")
            st.write(f"- **Câu chọn giới tính (Nhóm 3)**: {score_gender} / {total_gender} câu đúng")
