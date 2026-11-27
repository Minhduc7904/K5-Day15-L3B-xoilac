"""Luồng chính của Examind — NHÓM VIẾT. Đúng như sơ đồ ở spec.md §4 (nhánh cá nhân hóa là lát cắt đo).

`python run.py`, `python run.py eval` và `python run.py simulate` đều gọi answer(text).

Luồng (workflow cố định, một agent; bước quyết định bằng quy tắc, model chỉ để diễn đạt lại):
  1. Chặn trước AI: tấn công (bỏ qua hướng dẫn, in đáp án, sửa điểm), xin đáp án để chép, ngoài môn Toán → từ chối.
  2. Chọn nhánh: kỳ thi có cấu trúc sẵn (nhánh A, chưa có cấu trúc xác thực → thu hẹp) · chương yếu của học sinh
     (nhánh B) · chương học sinh tự nêu.
  3. Nhánh B: get_student_results → chưa có lịch sử / mâu thuẫn thì hỏi lại, không đoán → đề xuất cấu trúc (PREVIEW).
  4. Chỉ khi học sinh xác nhận cấu trúc: search_question_bank → build_exam_draft (bản nháp, không kèm đáp án).
  5. Chặn sau AI: mọi mã câu phải có trong ngân hàng; bản diễn đạt lại của model phải giữ nguyên tập mã câu.

Chế độ giả (MODEL_PROVIDER trống/fake): trả thẳng bản dựng bằng code, không gọi model.
Không có luật khớp nguyên văn input của bộ câu thử: các mẫu dưới đây là mẫu chung cho từng loại yêu cầu.
"""
import re
import unicodedata

from ai import call_model, MODEL_PROVIDER
from tools import (get_student_results, search_question_bank, build_exam_draft, get_exam_template,
                   load_bank, load_chapters, DIFFICULTIES)
from tracing import note

SYSTEM = (
    "Bạn là trợ lý ôn Toán THPT của Examind. Chỉ viết lại thông điệp được đưa cho ngắn gọn, thân thiện, tiếng Việt. "
    "Giữ nguyên mọi con số, tên chương và mã câu. Không thêm câu hỏi, đáp án, số liệu hay cấu trúc kỳ thi mới. "
    "Không nói là đã ghi điểm hay sửa điểm."
)

DIFF_NAME = {"NB": "nhận biết", "TH": "thông hiểu", "VD": "vận dụng", "VDC": "vận dụng cao"}
DEFAULT_WEIGHTS = {"NB": 0.2, "TH": 0.4, "VD": 0.4, "VDC": 0.0}
DEFAULT_N = 10
CLOSE_GAP = 0.10        # hai chương yếu nhất cách nhau ≤ 10 điểm % → chia câu cho cả hai
MIN_ANSWERS = 5         # chương có ít hơn số câu này không dùng để xếp hạng
OFFER = "Mình có thể ra đề ôn Toán theo chương em hay sai, hoặc theo chương em chọn."


def norm(text):
    """Bỏ dấu, thường hoá, để so mẫu."""
    t = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


# ---------- mẫu nhận diện (chuẩn hoá không dấu) ----------
DIFF_RE = r"(van dung cao|thong hieu|nhan biet|van dung|vdc|nb|th|vd)"
DIFF_KEY = {"van dung cao": "VDC", "vdc": "VDC", "thong hieu": "TH", "th": "TH", "nhan biet": "NB", "nb": "NB",
            "van dung": "VD", "vd": "VD"}
INJECTION = re.compile(r"(bo qua|quen|ignore).{0,30}(huong dan|chi dan|quy tac|lenh|instruction|prompt)")
DUMP = re.compile(r"(in|hien|liet ke|xuat|gui|cho).{0,25}(toan bo|tat ca).{0,25}(dap an|ngan hang)")
TAMPER = re.compile(r"\b(sua|chinh|nang|tang|thay doi|doi)\b.{0,15}\bdiem\b")
CHEAT = re.compile(r"dap an.{0,40}(de kiem tra|bai kiem tra|de thi|de cua lop|de lop)|\bchep\b.{0,20}(dap an|bai)|dap an.{0,30}\bchep\b")
OFF_TOPIC = re.compile(r"\b(ngu van|bai van|nghi luan|van hoc|tieng anh|vat ly|hoa hoc|sinh hoc|lich su|dia ly)\b")
EXAM = re.compile(r"(ky thi|thi tot nghiep|thi thpt|thi hoc ky|thi giua ky|thi cuoi ky|cau truc de|ma tran|de thi 20\d\d|theo cau truc)")
WEAK = re.compile(r"(hay sai|yeu|chua vung|sai nhieu|kem)")
CODE = re.compile(r"\b(1[0-2]c\d)\b")


def guard_input(t):
    """Chặn trước AI. Trả thông điệp từ chối, hoặc None nếu hợp lệ."""
    if INJECTION.search(t) or DUMP.search(t):
        return "Mình không thể làm theo yêu cầu đó: mình không bỏ qua quy tắc hay đưa đáp án của ngân hàng câu hỏi. " + OFFER
    if TAMPER.search(t):
        return "Mình không thể sửa điểm hay dữ liệu làm bài, điểm không do mình quyết định. " + OFFER
    if CHEAT.search(t):
        return "Mình không đưa đáp án đề kiểm tra để chép. Nếu em muốn luyện, " + OFFER[0].lower() + OFFER[1:]
    if OFF_TOPIC.search(t):
        return "Mình chỉ hỗ trợ ôn môn Toán THPT nên không làm được việc này. " + OFFER
    return None


def chapter_label(code):
    name = load_chapters().get(code, "")
    return "%s %s" % (code, name.capitalize()) if name else code


def allocate(n, weights):
    """Chia n câu theo trọng số (phương pháp phần dư lớn nhất)."""
    total = sum(weights.values())
    if n <= 0 or total <= 0:
        return {}
    raw = {k: n * w / total for k, w in weights.items() if w > 0}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: n - sum(out.values())]:
        out[k] += 1
    return {k: v for k, v in out.items() if v}


def parse_structure(t, default_n=DEFAULT_N):
    """Rút cấu trúc (chương, số câu, độ khó) từ lời học sinh. Trả dict hoặc None nếu thiếu chương."""
    chapters = CODE.findall(t)
    chapters = [c.upper() for c in dict.fromkeys(chapters) if c.upper() in load_chapters()]
    if not chapters:
        return None
    per = {c.upper(): int(n) for c, n in re.findall(r"(1[0-2]c\d)\s*\((\d+)\s*cau\)", t)}
    m = re.search(r"(\d+)\s*cau", t)
    n = int(m.group(1)) if m else default_n
    explicit = {DIFF_KEY[d]: int(k) for k, d in re.findall(r"(\d+)\s*(?:cau\s*)?" + DIFF_RE + r"\b", t)}
    only = re.search(r"toan\s+(?:bo\s+)?(?:cau\s+)?" + DIFF_RE + r"\b", t)
    exclude = {DIFF_KEY[d] for d in re.findall(r"(?:khong|bo|dung|tranh)\s+(?:lay\s+)?(?:cac\s+)?(?:cau\s+)?" + DIFF_RE + r"\b", t)}
    if only:
        mix_w = {DIFF_KEY[only.group(1)]: 1.0}
    elif explicit and sum(explicit.values()) > 0:
        mix_w = {k: float(v) for k, v in explicit.items()}
        if not m or sum(explicit.values()) <= n:
            n = sum(explicit.values()) if not per else n
    else:
        mix_w = {k: w for k, w in DEFAULT_WEIGHTS.items() if k not in exclude}
    mix_w = {k: w for k, w in mix_w.items() if k not in exclude and k in DIFFICULTIES}
    if per:
        chap_n = {c: per.get(c, 0) for c in chapters}
        n = sum(chap_n.values()) or n
    else:
        chap_n = allocate(n, {c: 1.0 for c in chapters})
    return {"chuong": chap_n, "so_cau": sum(chap_n.values()), "trong_so_do_kho": mix_w, "loai_tru": sorted(exclude)}


def mix_text(weights, n):
    mix = allocate(n, weights)
    return ", ".join("%d %s" % (v, DIFF_NAME[k]) for k, v in mix.items())


def preview(structure, why):
    """Thông điệp PREVIEW cấu trúc đề (chưa có mã câu)."""
    lines = ["Đề xuất cấu trúc đề ôn (chưa tạo đề):"]
    parts = []
    for c, n in structure["chuong"].items():
        lines.append("- %s: %d câu (%s)" % (chapter_label(c), n, mix_text(structure["trong_so_do_kho"], n)))
        parts.append("%s (%d câu)" % (c, n))
    if why:
        lines.append(why)
    if structure["loai_tru"]:
        lines.append("Đã bỏ mức: %s." % ", ".join(DIFF_NAME[d] for d in structure["loai_tru"]))
    lines.append("Em xác nhận hoặc chỉnh bằng lời (đổi chương, số câu, độ khó) nhé. Để mình tạo đề nháp, nhắn: "
                 "\"Xác nhận cấu trúc: chương %s. Tạo đề nháp.\"" % ", ".join(parts))
    return "\n".join(lines)


def personalized(student_id, t):
    res = get_student_results(student_id)
    if not res["found"]:
        note("dừng: chưa có lịch sử, hỏi lại chương")
        return ("Mình chưa có lịch sử làm bài của %s nên chưa biết chương em hay sai, và mình không đoán. "
                "Em muốn ôn chương nào? Ví dụ: %s." % (student_id, "; ".join(chapter_label(c) for c in sorted(load_chapters()) if c.startswith("12"))))
    ranked = [c for c in res["chapters"] if c["tong"] >= MIN_ANSWERS]
    if res["mau_thuan"]:
        note("dừng: kết quả mâu thuẫn, hỏi lại")
        cand = ["- %s: đúng %d/%d (%d%%)" % (chapter_label(c["chuong"]), c["dung"], c["tong"], round(100 * c["ti_le_dung"])) for c in ranked[:3]]
        return ("Kết quả làm bài của %s có chỗ mâu thuẫn (khoảng %d%% số câu vừa đúng vừa sai trong cùng một lượt), "
                "nên mình chưa xác định chắc chương yếu. Các chương đang thấp nhất:\n%s\nEm muốn ôn chương nào trong số này, hay chương khác?"
                % (student_id, round(100 * res["ti_le_cau_trai_nhau"]), "\n".join(cand)))
    if not ranked:
        return "Em làm chưa đủ nhiều câu ở mỗi chương để mình xác định chương yếu. Em muốn ôn chương nào?"
    top = ranked[:2] if len(ranked) >= 2 and ranked[1]["ti_le_dung"] - ranked[0]["ti_le_dung"] <= CLOSE_GAP else ranked[:1]
    m = re.search(r"(\d+)\s*cau", t)
    n = int(m.group(1)) if m else DEFAULT_N
    if len(top) == 2:
        first = round(n * 0.6)
        chap_n = {top[0]["chuong"]: first, top[1]["chuong"]: n - first}
    else:
        chap_n = {top[0]["chuong"]: n}
    base = parse_structure(" ".join(c.lower() for c in chap_n) + " " + t, n)
    structure = {"chuong": chap_n, "so_cau": n,
                 "trong_so_do_kho": base["trong_so_do_kho"] if base else dict(DEFAULT_WEIGHTS),
                 "loai_tru": base["loai_tru"] if base else []}
    why = "Lý do: " + "; ".join(
        "%s đúng %d/%d (%d%%), sai %d câu" % (c["chuong"], c["dung"], c["tong"], round(100 * c["ti_le_dung"]), c["tong"] - c["dung"]) for c in top
    ) + (", hai chương yếu gần nhau nên chia câu cho cả hai." if len(top) == 2 else ".")
    note("preview nhánh cá nhân hoá: %s" % list(chap_n))
    return preview(structure, why)


def build(structure):
    """Tìm câu theo cấu trúc đã xác nhận và dựng bản nháp. Trả (thông điệp, tập mã câu)."""
    chosen, shortage = [], []
    for c, n in structure["chuong"].items():
        for d, k in allocate(n, structure["trong_so_do_kho"]).items():
            res = search_question_bank(chapter=c, difficulty=d, n=k, exclude=tuple(chosen))
            chosen += res["ma_cau"]
            if res["thieu"]:
                shortage.append("%s %s: chỉ có %d/%d câu" % (c, DIFF_NAME[d], len(res["ma_cau"]), k))
    draft = build_exam_draft(structure=structure, question_ids=chosen)
    bank = load_bank()
    cau = [q for q in draft["cau"] if q["ma_cau"] in bank]      # chặn sau AI: chỉ câu thuộc ngân hàng
    if draft["ma_cau_khong_hop_le"]:
        note("loại mã không hợp lệ: %s" % draft["ma_cau_khong_hop_le"])
    if not cau:
        return "Ngân hàng chưa có câu nào phù hợp cấu trúc này. Em thử đổi chương hoặc độ khó nhé.", set()
    lines = ["BẢN NHÁP đề ôn (chưa chính thức, chờ em duyệt). Chưa kèm đáp án.", ""]
    for q in cau:
        lines.append("Câu %d [%s · %s · %s] %s" % (q["stt"], q["ma_cau"], q["chuong"], q["do_kho"], q["noi_dung"].strip()))
        for ch in q["lua_chon"]:
            lines.append("   %s. %s" % (ch["nhan"], ch["noi_dung"]))
    want = structure["so_cau"]
    if len(cau) < want or shortage:
        lines.append("")
        lines.append("Lưu ý: ngân hàng không đủ câu như yêu cầu. Mình chỉ đưa %d/%d câu có thật, thiếu %d câu, không tự bịa thêm. %s"
                     % (len(cau), want, want - len(cau), "; ".join(shortage)))
    return "\n".join(lines), {q["ma_cau"] for q in cau}


def polish(facts):
    """Diễn đạt lại thông điệp không chứa câu hỏi. Chế độ giả hoặc lỗi → trả nguyên bản dựng bằng code."""
    if MODEL_PROVIDER == "fake":
        return facts
    out = call_model(SYSTEM, "Viết lại thông điệp sau, giữ nguyên số liệu và tên chương:\n" + facts)["text"]
    if re.findall(r"Q\d{5}", out):               # chặn sau AI: model không được thêm mã câu
        note("bỏ bản diễn đạt lại: có mã câu lạ")
        return facts
    return out


def answer(text: str) -> dict:
    t = norm(text)
    refusal = guard_input(t)
    if refusal:
        note("chặn trước AI: từ chối")
        return {"output": polish(refusal)}

    m = re.search(r"\bhs\d+\b", t)
    student = m.group(0).upper() if m else None

    if EXAM.search(t):                                   # nhánh A: kỳ thi — chưa có cấu trúc xác thực
        res = get_exam_template(exam_code=text.strip())
        if not res["co"]:
            note("thu hẹp: kỳ thi chưa có cấu trúc xác thực")
            return {"output": polish("Mình chưa có cấu trúc đã xác thực nguồn cho kỳ thi này nên không nêu số câu hay phân bố chương, "
                                     "để khỏi nói sai. " + OFFER)}

    structure = parse_structure(t)
    if structure:                                        # học sinh nêu chương cụ thể
        if re.search(r"tao de|xac nhan", t) and re.search(r"\d+\s*cau", t):
            msg, ids = build(structure)
            note("dựng đề nháp: %d câu" % len(ids))
            return {"output": msg}                       # bản nháp có câu hỏi: không để model viết lại
        return {"output": polish(preview(structure, ""))}

    phrase = re.search(r"chuong\s+([a-z0-9 ]+?)(?:\s+cho\b|\s+\d|[,.;:!?(]|$)", t)
    if phrase and not WEAK.search(phrase.group(1)):      # chương học sinh gọi tên nhưng không có trong ngân hàng
        names = [norm(v) for v in load_chapters().values()]
        if not any(phrase.group(1).strip() in nm for nm in names):
            note("thu hẹp: chương không có trong ngân hàng")
            shown = re.search(r"chương\s+([^\d,.;:!?(]+?)(?:\s+cho\b|\s+\d|[,.;:!?(]|$)", text, re.I)
            name = (shown.group(1) if shown else phrase.group(1)).strip()
            return {"output": polish("Ngân hàng hiện chưa có câu hỏi về chương \"%s\", nên mình không bịa câu. Em chọn chương khác nhé, ví dụ: %s."
                                     % (name, "; ".join(chapter_label(c) for c in sorted(load_chapters()) if c.startswith("12"))))}

    if WEAK.search(t) or re.search(r"\b(ra de|on)\b", t):
        if not student:
            return {"output": "Em cho mình mã học sinh (ví dụ HS01) để mình xem lịch sử làm bài nhé."}
        return {"output": polish(personalized(student, t))}

    return {"output": polish("Em muốn ôn chương nào, hay để mình chọn theo chương em hay sai? " + OFFER)}
