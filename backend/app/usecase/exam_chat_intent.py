"""Hiểu tin nhắn của học sinh bằng quy tắc (issue #4). Hàm thuần, không gọi model.

Mẫu chặn và mẫu nhận diện chép từ codebase/agent.py (lát cắt đã đo) để backend và bản chạy thử cư xử giống nhau.
Đây là mẫu chung theo loại yêu cầu, không khớp nguyên văn câu trong eval/benchmark.csv (luật AGENTS.md).
"""
import re
import unicodedata
from dataclasses import dataclass, field

from app.usecase.exam_preview_rules import MAX_TOTAL, PreviewEdit

OFFER = "Mình có thể ra đề ôn Toán theo chương em hay sai, hoặc theo chương em chọn."

DIFF_RE = r"(van dung cao|thong hieu|nhan biet|van dung|vdc|nb|th|vd)"
DIFF_KEY = {"van dung cao": "VDC", "vdc": "VDC", "thong hieu": "TH", "th": "TH", "nhan biet": "NB", "nb": "NB",
            "van dung": "VD", "vd": "VD"}
INJECTION = re.compile(r"(bo qua|quen|ignore).{0,30}(huong dan|chi dan|quy tac|lenh|instruction|prompt)")
DUMP = re.compile(r"(in|hien|liet ke|xuat|gui|cho).{0,25}(toan bo|tat ca).{0,25}(dap an|ngan hang)")
TAMPER = re.compile(r"\b(sua|chinh|nang|tang|thay doi|doi)\b.{0,15}\bdiem\b")
CHEAT = re.compile(r"dap an.{0,40}(de kiem tra|bai kiem tra|de thi|de cua lop|de lop)|\bchep\b.{0,20}(dap an|bai)"
                   r"|dap an.{0,30}\bchep\b")
OFF_TOPIC = re.compile(r"\b(ngu van|bai van|nghi luan|van hoc|tieng anh|vat ly|hoa hoc|sinh hoc|lich su|dia ly)\b")
EXAM = re.compile(r"(ky thi|thi tot nghiep|thi thpt|thi hoc ky|thi giua ky|thi cuoi ky|cau truc de|ma tran"
                  r"|de thi 20\d\d|theo cau truc|giua ky|cuoi ky|giua hoc ky|cuoi hoc ky|\bhsa\b|\btsa\b"
                  r"|danh gia nang luc|danh gia tu duy)")
WEAK = re.compile(r"(hay sai|yeu|chua vung|sai nhieu|kem)")
CONFIRM = re.compile(r"\b(xac nhan|dong y|tao de|chot)\b")
CODE = re.compile(r"\b(1[0-2]c\d+)\b")
COUNT = re.compile(r"(\d+)\s*cau")
CHAPTER_COUNT = re.compile(r"(1[0-2]c\d+)\s*\((\d+)\s*cau\)")
ONLY = re.compile(r"toan\s+(?:bo\s+)?(?:cau\s+)?" + DIFF_RE + r"\b")
EXCLUDE = re.compile(r"(?:khong|bo|dung|tranh)\s+(?:lay\s+)?(?:cac\s+)?(?:cau\s+)?(?:muc\s+)?" + DIFF_RE + r"\b")
MIX = re.compile(r"(\d+)\s*(?:cau\s*)?" + DIFF_RE + r"\b")
NEXT_PRACTICE = re.compile(r"(?:tao|ra|lam) de on tiep(?:\s+(\d+)\s+cau(?:\s+" + DIFF_RE
                           + r")?)?(?:\s+(?:nhe|cho em))?[.!?]*")
GRADE = re.compile(r"\blop\s*(1[0-2])\b")
YEAR = re.compile(r"\b(20\d\d)\b")


def norm(text: str) -> str:
    """Bỏ dấu, thường hoá, để so mẫu."""
    t = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


def refusal(t: str) -> str | None:
    """Chặn trước AI. t đã chuẩn hoá. Trả lời từ chối, hoặc None nếu hợp lệ."""
    if INJECTION.search(t) or DUMP.search(t):
        return "Mình không thể làm theo yêu cầu đó: mình không bỏ qua quy tắc hay đưa đáp án của ngân hàng câu hỏi. " + OFFER
    if TAMPER.search(t):
        return "Mình không thể sửa điểm hay dữ liệu làm bài, điểm không do mình quyết định. " + OFFER
    if CHEAT.search(t):
        return "Mình không đưa đáp án đề kiểm tra để chép. Nếu em muốn luyện, " + OFFER[0].lower() + OFFER[1:]
    if OFF_TOPIC.search(t):
        return "Mình chỉ hỗ trợ ôn môn Toán THPT nên không làm được việc này. " + OFFER
    return None


def exam_request(t: str) -> dict | None:
    """Nhận diện loại kỳ thi (mã như exams.type_of_exam), khối và năm. None nếu không phải yêu cầu theo kỳ thi."""
    if not EXAM.search(t):
        return None
    semester = "2" if re.search(r"(ky|hoc ky|hk)\s*(2|ii)\b", t) else "1" if re.search(r"(ky|hoc ky|hk)\s*(1|i)\b", t) else None
    exam_type = None
    if re.search(r"tot nghiep|thi thpt|thpt quoc gia", t):
        exam_type = "THPT"
    elif re.search(r"\bhsa\b|danh gia nang luc", t):
        exam_type = "HSA"
    elif re.search(r"\btsa\b|danh gia tu duy", t):
        exam_type = "TSA"
    elif re.search(r"giua", t) and semester:
        exam_type = "GK" + semester
    elif re.search(r"cuoi", t) and semester:
        exam_type = "CK" + semester
    grade = GRADE.search(t)
    year = YEAR.search(t)
    return {
        "exam_type": exam_type,
        "grade": int(grade.group(1)) if grade else None,
        "version_label": year.group(1) if year else None,
    }


def parse_edit(t: str) -> PreviewEdit:
    """Rút các chỉnh sửa có trong lời học sinh (chương, số câu, độ khó). Rỗng nếu không có gì."""
    data: dict = {}
    per = {c.upper(): int(n) for c, n in CHAPTER_COUNT.findall(t)}
    codes = [c.upper() for c in dict.fromkeys(CODE.findall(t))]
    if per:
        data["chapter_counts"] = per
    elif codes:
        data["chapter_codes"] = codes
    only = ONLY.search(t)
    excluded = sorted({DIFF_KEY[d] for d in EXCLUDE.findall(t)})
    t_no_exclude = EXCLUDE.sub(" ", t)
    mix = {DIFF_KEY[d]: int(k) for k, d in MIX.findall(t_no_exclude)}
    if only:
        data["only_difficulty"] = DIFF_KEY[only.group(1)]
    elif mix and sum(mix.values()) > 0:
        data["difficulty_counts"] = mix
    if excluded:
        data["exclude_difficulties"] = excluded
    # Tổng số câu: số đứng trước "câu" mà không phải phân bố độ khó ("3 câu thông hiểu") hay số câu theo chương.
    t_total = CHAPTER_COUNT.sub(" ", MIX.sub(" ", t_no_exclude))
    m = COUNT.search(t_total)
    if m:
        data["total"] = int(m.group(1))
    elif "difficulty_counts" in data and "chapter_counts" not in data:
        data["total"] = sum(data["difficulty_counts"].values())
    if data.get("total") is not None and not 1 <= data["total"] <= MAX_TOTAL:
        del data["total"]          # số vượt giới hạn: usecase báo lại dựa trên Intent.asked_total
    if any(not 1 <= n <= MAX_TOTAL for n in data.get("chapter_counts", {}).values()):
        del data["chapter_counts"]
    return PreviewEdit(**data)


@dataclass
class Intent:
    """Kết quả đọc một tin nhắn. kind: refuse · exam · confirm · edit · weak · unknown."""

    kind: str
    text: str = ""
    edit: PreviewEdit = field(default_factory=PreviewEdit)
    exam: dict | None = None
    asked_total: int | None = None


def next_practice(t: str) -> Intent | None:
    """Nhận yêu cầu ôn tiếp độc lập và số câu/mức độ nếu học sinh nêu."""
    match = NEXT_PRACTICE.fullmatch(t.strip())
    if match is None:
        return None
    return Intent("weak", edit=parse_edit(t), asked_total=int(match[1]) if match[1] else None)


def read(text: str) -> Intent:
    t = norm(text)
    msg = refusal(t)
    if msg:
        return Intent("refuse", text=msg)
    next_exam = next_practice(t)
    if next_exam:
        return next_exam
    raw_total = COUNT.search(t)
    edit = parse_edit(t)
    asked = int(raw_total.group(1)) if raw_total else None
    exam = exam_request(t)
    if exam is not None:
        return Intent("exam", exam=exam, edit=edit, asked_total=asked)
    if re.search(r"\b(tao de|ra de|on)\b.{0,35}\b(on tiep|theo lich su|hay sai|vua lam)\b", t):
        return Intent("weak", edit=edit, asked_total=asked)
    if CONFIRM.search(t):
        return Intent("confirm", edit=edit, asked_total=asked)
    if edit.chapter_codes or edit.chapter_counts:
        return Intent("edit", edit=edit, asked_total=asked)
    if WEAK.search(t) or re.search(r"\b(ra de|on tap|on)\b", t):
        return Intent("weak", edit=edit, asked_total=asked)
    if not edit.is_empty():
        return Intent("edit", edit=edit, asked_total=asked)
    return Intent("unknown")
