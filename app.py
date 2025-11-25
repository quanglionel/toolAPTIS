import re
import random

import streamlit as st
from docx import Document

# ==========================
#  CẤU HÌNH BAN ĐẦU
# ==========================

st.set_page_config(page_title="Tool luyện đề từ nhiều Test", layout="wide")

# Nhận diện đầu mỗi Question trong file Word: "Question 1:", "Question 16:"
QUESTION_START_PATTERN = re.compile(
    r"^\s*Question\s*\d+\s*[\.:)\-/]", re.IGNORECASE
)

# Regex phụ
ANSWER_PATTERN = re.compile(r"Answer\s*:\s*(.+)", re.IGNORECASE)
OPTION_PATTERN = re.compile(r"^\s*([A-D])[\.\)]\s*(.+)", re.IGNORECASE)


# ==========================
#  HÀM TÁCH QUESTION TỪ WORD
# ==========================

def extract_raw_questions_from_docx(file) -> list[str]:
    """
    Đọc file .docx, tách thành các block tương ứng Question 1, Question 2, ...
    """
    doc = Document(file)
    raw_lines = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            raw_lines.append(text)

    questions = []
    current_block = []

    def flush_block():
        nonlocal current_block
        if current_block:
            questions.append("\n".join(current_block).strip())
        current_block = []

    for line in raw_lines:
        if QUESTION_START_PATTERN.match(line):
            flush_block()
            current_block.append(line)
        else:
            current_block.append(line)

    flush_block()
    return questions


# ==========================
#  CÁC HÀM PARSE TỪNG LOẠI CÂU
# ==========================

def parse_single_mcq(lines):
    """
    Parse một câu trắc nghiệm đơn:
    - stem
    - Options A/B/C/D
    - Answer: X
    """
    stem_lines = []
    options = {}
    answer = None

    for line in lines:
        # Dòng Answer: X
        m_ans = ANSWER_PATTERN.search(line)
        if m_ans:
            raw_ans = m_ans.group(1).strip()
            if raw_ans:
                answer = raw_ans[0].upper()
            continue

        # Dòng A. / B) ...
        m_opt = OPTION_PATTERN.match(line)
        if m_opt:
            label = m_opt.group(1).upper()
            txt = m_opt.group(2).strip()
            options[label] = txt
            continue

        stem_lines.append(line)

    if not answer or not options:
        return None

    stem = "\n".join(stem_lines).strip()
    return {"stem": stem, "options": options, "answer": answer}


def parse_group1_mcq(block: str):
    """
    Nhóm 1: Question 1–13 → 1 câu trắc nghiệm đơn.
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]

    # Bỏ dòng "Question 1:" / "Question 5:" ...
    if lines and QUESTION_START_PATTERN.match(lines[0]):
        lines = lines[1:]

    if not lines:
        return None

    return parse_single_mcq(lines)


def parse_group4_block(block: str):
    """
    Nhóm 4: Question 16–17, dạng:

    Question 16:
    [intro...]
    Câu 1: ...
    A. ...
    B. ...
    C. ...
    Answer: X

    Câu 2: ...
    A. ...
    B. ...
    C. ...
    Answer: Y
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return None

    # Bỏ dòng "Question 16:" / "Question 17:"
    if QUESTION_START_PATTERN.match(lines[0]):
        lines = lines[1:]

    if not lines:
        return None

    # Tách intro (các dòng trước "Câu 1")
    intro_lines = []
    body_lines = []
    started_body = False

    for line in lines:
        if not started_body and line.lstrip().lower().startswith("câu "):
            started_body = True
            body_lines.append(line)
        elif not started_body:
            intro_lines.append(line)
        else:
            body_lines.append(line)

    if not body_lines:
        # Không có "Câu 1" → fallback coi là 1 MCQ
        item = parse_single_mcq(lines)
        if not item:
            return None
        return {"mode": "single", "item": item}

    # Xác định các vị trí "Câu 1", "Câu 2", ...
    starts = []
    for idx, line in enumerate(body_lines):
        if line.lstrip().lower().startswith("câu "):
            starts.append(idx)

    if not starts:
        item = parse_single_mcq(body_lines)
        if not item:
            return None
        return {"mode": "single", "item": item}

    sub_items = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(body_lines)
        sub_lines = body_lines[s:e]
        item = parse_single_mcq(sub_lines)
        if item:
            sub_items.append(item)

    intro = "\n".join(intro_lines).strip()

    if len(sub_items) >= 2:
        # Đúng format 2 câu con
        return {"mode": "multi", "intro": intro, "items": sub_items}
    elif sub_items:
        # Chỉ parse được 1 câu → vẫn cho chạy dạng single
        return {"mode": "single", "item": sub_items[0]}
    else:
        return None


def parse_order_question(block: str):
    """
    Nhóm 2: Question 14 - dạng sắp xếp:
    - Bỏ dòng "Question 14:"
    - TẤT CẢ các dòng còn lại đều là item cần sắp xếp (thứ tự đúng).
      Ví dụ:

      Question 14:
      Mountain biking
      Going for a run
      Walking
      Horse riding
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return None

    # Bỏ header "Question 14:"
    if QUESTION_START_PATTERN.match(lines[0]):
        lines = lines[1:]

    if not lines:
        return None

    items = []
    for line in lines:
        if ANSWER_PATTERN.search(line):
            continue
        items.append(line)

    if len(items) < 2:
        return None

    # Đề bài chung cho tất cả Q14
    prompt = "Sắp xếp các mục sau theo đúng thứ tự:"
    return {"prompt": prompt, "items": items}


def parse_gender_block(block: str):
    """
    Nhóm 3: Question 15 - 4 câu con '... - woman/man/both'
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    items = []

    for line in lines:
        if QUESTION_START_PATTERN.match(line):
            continue

        # Bắt '... - woman', '... - man', '... - both'
        m = re.match(r"(.+)-\s*(woman|man|both)\s*$", line, re.IGNORECASE)
        if m:
            stem = m.group(1).strip()
            gender = m.group(2).strip().lower()
            items.append({"stem": stem, "gender": gender})

    if not items:
        return None

    return {"items": items}


def get_group_for_index(idx: int) -> int | None:
    """
    Mapping:
    - Nhóm 1: Question 1–13
    - Nhóm 2: Question 14
    - Nhóm 3: Question 15
    - Nhóm 4: Question 16–17
    """
    if 1 <= idx <= 13:
        return 1
    if idx == 14:
        return 2
    if idx == 15:
        return 3
    if idx in (16, 17):
        return 4
    return None


# ==========================
#  SESSION STATE
# ==========================

if "question_bank" not in st.session_state:
    st.session_state.question_bank = {
        1: [],  # Nhóm 1: MCQ đơn
        2: [],  # Nhóm 2: ORDER
        3: [],  # Nhóm 3: GENDER BLOCK
        4: [],  # Nhóm 4: MCQ (1 hoặc nhiều câu con)
    }

if "current_exam" not in st.session_state:
    st.session_state.current_exam = []


# ==========================
#  UI CHÍNH
# ==========================

st.title("📚 Tool luyện đề từ nhiều Test (17 câu cố định thứ tự)")

st.markdown(
    """
**Cấu trúc mỗi Test**

- **Q1–13** → Nhóm 1: trắc nghiệm A/B/C/D, có `Answer: X`  
- **Q14**   → Nhóm 2: sắp xếp thứ tự (chỉ có 4 dòng item, không intro)  
- **Q15**   → Nhóm 3: 4 câu con `... - woman/man/both`  
- **Q16–17**→ Nhóm 4: mỗi Question có 2 câu con:
  `Câu 1: ... A/B/C ... Answer: X`  
  `Câu 2: ... A/B/C ... Answer: Y`

**Đề luyện tập (17 câu)**

- Câu 1–13: 13 câu random từ Nhóm 1  
- Câu 14: 1 câu từ Nhóm 2 (sắp xếp)  
- Câu 15: 1 block từ Nhóm 3 (4 câu con)  
- Câu 16–17: 2 block từ Nhóm 4 (mỗi block 2 câu con)  
"""
)

# --------- 1. UPLOAD TEST ---------

st.header("1️⃣ Upload đề thi (theo Test)")

col1, col2 = st.columns([1, 2])

with col1:
    test_id = st.number_input(
        "Nhập số Test (1–50):",
        min_value=1,
        max_value=50,
        value=1,
        step=1,
    )

with col2:
    uploaded_file = st.file_uploader(
        "📤 Chọn file đề thi (.docx) cho Test này",
        type=["docx"],
        key="file_uploader",
    )

if uploaded_file is not None and st.button("📥 Xử lý & thêm vào ngân hàng"):
    blocks = extract_raw_questions_from_docx(uploaded_file)

    if not blocks:
        st.error("Không tách được Question nào. Kiểm tra lại file.")
    else:
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
                            "items": parsed["items"],  # list các câu con
                        }
                    )
                added += 1

        st.success(f"✅ Đã thêm {added} Question/block từ Test {int(test_id)} vào ngân hàng.")


# --------- 2. THỐNG KÊ ---------

st.header("2️⃣ Thống kê ngân hàng câu hỏi")

counts = {g: len(st.session_state.question_bank[g]) for g in [1, 2, 3, 4]}

st.markdown(
    f"""
- Nhóm 1 (Q1–13, MCQ): **{counts[1]}** câu  
- Nhóm 2 (Q14, sắp xếp): **{counts[2]}** câu  
- Nhóm 3 (Q15, woman/man/both): **{counts[3]}** block  
- Nhóm 4 (Q16–17, multi MCQ): **{counts[4]}** block  
"""
)

# --------- 3. XEM LẠI TEST ĐÃ UPLOAD ---------

st.header("3️⃣ Xem lại Test đã upload")

# Lấy danh sách test_id hiện có
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
    )

    # Đếm số câu theo nhóm cho Test này
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

    # Hiển thị chi tiết theo nhóm
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


# --------- 4. TẠO ĐỀ 17 CÂU ---------

st.header("4️⃣ Tạo đề luyện tập 17 câu")

can_generate = (
    counts[1] >= 13
    and counts[2] >= 1
    and counts[3] >= 1
    and counts[4] >= 2
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
    if st.button("🎲 Tạo đề 17 câu (giữ thứ tự 1–17)"):
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


# --------- 5. LÀM ĐỀ & CHẤM ---------

if st.session_state.current_exam:
    st.header("5️⃣ Đề luyện tập & chấm điểm")

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
                options=["(Chưa chọn)"] + option_entries,
                key=f"mcq_{i}",
            )

            total_mcq += 1

            if chosen != "(Chưa chọn)":
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
                    options=["(Chưa chọn)"] + opt_entries,
                    key=f"mcq_multi_{i}_{j}",
                )

                total_mcq += 1

                if chosen != "(Chưa chọn)":
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
                    options=["(Chưa chọn)", "woman", "man", "both"],
                    key=f"gender_{i}_{j}",
                )
                if choice != "(Chưa chọn)":
                    total_gender += 1
                    if choice.lower() == item["gender"]:
                        st.success("✅ Đúng")
                        score_gender += 1
                    else:
                        st.error(f"❌ Sai. Đáp án: {item['gender']}")

        st.markdown("---")

    # --------- TỔNG KẾT ---------
    st.header("🧮 Tổng kết")

    st.write("### Kết quả theo nhóm:")

    st.write(f"- **Trắc nghiệm (Nhóm 1 & 4)**: {score_mcq} / {total_mcq} câu con đúng")
    st.write(f"- **Câu sắp xếp (Nhóm 2)**: {score_order} / {total_order} câu đúng")
    st.write(f"- **Câu chọn giới tính (Nhóm 3)**: {score_gender} / {total_gender} câu đúng")
