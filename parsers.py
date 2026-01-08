# -*- coding: utf-8 -*-
"""
Các hàm parse file Word (.docx) để trích xuất câu hỏi
"""
import re
from docx import Document


# ==========================
#  REGEX PATTERNS
# ==========================

# Nhận diện đầu mỗi Question trong file Word: "Question 1:", "Question 16:"
QUESTION_START_PATTERN = re.compile(
    r"^\s*Question\s*\d+\s*[\.:)\-/]", re.IGNORECASE
)

# Regex phụ
ANSWER_PATTERN = re.compile(r"Answer\s*:\s*(.+)", re.IGNORECASE)
# Cho phép "A." hoặc "A ." hoặc "A)" đều được
OPTION_PATTERN = re.compile(r"^\s*([A-D])\s*[\.\)]\s*(.+)", re.IGNORECASE)


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

    # Chỉ bỏ phần "Question X:" prefix, GIỮ LẠI phần stem nếu nằm cùng dòng
    if lines and QUESTION_START_PATTERN.match(lines[0]):
        lines[0] = QUESTION_START_PATTERN.sub("", lines[0]).strip()
        if not lines[0]:  # Nếu dòng trống sau khi bỏ prefix thì xóa
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

    # Chỉ bỏ phần "Question X:" prefix, GIỮ LẠI phần intro nếu nằm cùng dòng
    if QUESTION_START_PATTERN.match(lines[0]):
        lines[0] = QUESTION_START_PATTERN.sub("", lines[0]).strip()
        if not lines[0]:  # Nếu dòng trống sau khi bỏ prefix thì xóa
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
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return None

    # Chỉ bỏ phần "Question 14:" prefix, GIỮ LẠI phần nội dung nếu nằm cùng dòng
    if QUESTION_START_PATTERN.match(lines[0]):
        lines[0] = QUESTION_START_PATTERN.sub("", lines[0]).strip()
        if not lines[0]:  # Nếu dòng trống sau khi bỏ prefix thì xóa
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
