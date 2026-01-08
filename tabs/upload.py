# -*- coding: utf-8 -*-
"""
Tab Upload - Upload nhiều đề thi cùng lúc
"""
import streamlit as st
from parsers import (
    extract_raw_questions_from_docx,
    get_group_for_index,
    parse_group1_mcq,
    parse_order_question,
    parse_gender_block,
    parse_group4_block,
)
from storage import save_question_bank


def process_single_test(uploaded_file, test_id, existing_tests):
    """Xử lý 1 file đề thi và thêm vào ngân hàng"""
    if int(test_id) in existing_tests:
        return False, f"🚫 Test {int(test_id)} đã tồn tại!"
    
    blocks = extract_raw_questions_from_docx(uploaded_file)
    if not blocks:
        return False, f"❌ Test {test_id}: Không tách được Question nào."
    
    added = 0
    for idx, block in enumerate(blocks, start=1):
        if idx > 17:
            break
        
        group = get_group_for_index(idx)
        if group is None:
            continue
        
        # ----- Nhóm 1: MCQ đơn -----
        if group == 1:
            parsed = parse_group1_mcq(block)
            if not parsed:
                continue
            item = parsed
            st.session_state.question_bank[group].append(
                {
                    "type": "mcq",
                    "group": group,
                    "test_id": int(test_id),
                    "index_in_test": idx,
                    "stem": item["stem"],
                    "options": item["options"],
                    "answer": item["answer"],
                }
            )
            added += 1
        
        # ----- Nhóm 2: ORDER -----
        elif group == 2:
            parsed = parse_order_question(block)
            if not parsed:
                continue
            st.session_state.question_bank[group].append(
                {
                    "type": "order",
                    "group": group,
                    "test_id": int(test_id),
                    "index_in_test": idx,
                    "prompt": parsed["prompt"],
                    "items": parsed["items"],
                }
            )
            added += 1
        
        # ----- Nhóm 3: GENDER BLOCK -----
        elif group == 3:
            parsed = parse_gender_block(block)
            if not parsed:
                continue
            st.session_state.question_bank[group].append(
                {
                    "type": "gender_block",
                    "group": group,
                    "test_id": int(test_id),
                    "index_in_test": idx,
                    "items": parsed["items"],
                }
            )
            added += 1
        
        # ----- Nhóm 4: MCQ 1 hoặc nhiều câu con -----
        elif group == 4:
            parsed = parse_group4_block(block)
            if not parsed:
                continue
            
            if parsed["mode"] == "single":
                item = parsed["item"]
                st.session_state.question_bank[group].append(
                    {
                        "type": "mcq",
                        "group": group,
                        "test_id": int(test_id),
                        "index_in_test": idx,
                        "stem": item["stem"],
                        "options": item["options"],
                        "answer": item["answer"],
                    }
                )
            else:  # multi
                st.session_state.question_bank[group].append(
                    {
                        "type": "mcq_multi",
                        "group": group,
                        "test_id": int(test_id),
                        "index_in_test": idx,
                        "intro": parsed["intro"],
                        "items": parsed["items"],
                    }
                )
            added += 1
    
    return True, f"✅ Test {test_id}: Đã thêm {added} câu."


def render_upload_tab(tab):
    """Render tab upload đề thi"""
    with tab:
        st.header("1️⃣ Upload đề thi (nhiều Test cùng lúc)")
        
        # Khởi tạo số lượng form upload trong session
        if "num_upload_forms" not in st.session_state:
            st.session_state.num_upload_forms = 1
        
        st.markdown("**Thêm nhiều đề thi cùng lúc:**")
        
        # Nút thêm/bớt form
        col_add, col_remove = st.columns(2)
        with col_add:
            if st.button("➕ Thêm đề", key="add_form"):
                st.session_state.num_upload_forms += 1
                st.rerun()
        with col_remove:
            if st.button("➖ Bớt đề", key="remove_form") and st.session_state.num_upload_forms > 1:
                st.session_state.num_upload_forms -= 1
                st.rerun()
        
        st.markdown("---")
        
        # Tạo các form upload động
        upload_data = []
        for i in range(st.session_state.num_upload_forms):
            st.markdown(f"### 📄 Đề {i + 1}")
            col1, col2 = st.columns([1, 3])
            
            with col1:
                test_id = st.number_input(
                    f"Số Test:",
                    min_value=1,
                    max_value=50,
                    value=i + 1,
                    step=1,
                    key=f"test_id_{i}",
                )
            
            with col2:
                uploaded_file = st.file_uploader(
                    f"Chọn file .docx",
                    type=["docx"],
                    key=f"file_{i}",
                )
            
            upload_data.append({"test_id": test_id, "file": uploaded_file})
        
        st.markdown("---")
        
        # Danh sách test đã tồn tại
        existing_tests = {
            q["test_id"]
            for group in st.session_state.question_bank.values()
            for q in group
        }
        
        # Nút xử lý tất cả
        if st.button("📥 Xử lý & thêm TẤT CẢ vào ngân hàng", key="upload_all_button", type="primary"):
            results = []
            success_count = 0
            
            for data in upload_data:
                if data["file"] is not None:
                    success, msg = process_single_test(data["file"], data["test_id"], existing_tests)
                    results.append(msg)
                    if success:
                        success_count += 1
                        # Cập nhật existing_tests để check trùng
                        existing_tests.add(int(data["test_id"]))
            
            if results:
                st.markdown("### 📊 Kết quả xử lý:")
                for r in results:
                    if r.startswith("✅"):
                        st.success(r)
                    else:
                        st.error(r)
                st.info(f"**Tổng cộng:** {success_count}/{len([d for d in upload_data if d['file']])} đề được xử lý thành công.")
                
                # Tự động lưu dữ liệu sau khi upload thành công
                if success_count > 0:
                    save_question_bank(st.session_state.question_bank)
                    st.success("💾 Dữ liệu đã được lưu tự động!")
            else:
                st.warning("⚠️ Chưa có file nào được chọn!")
