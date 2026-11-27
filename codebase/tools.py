"""Công cụ của Examind — NHÓM VIẾT. Khớp bảng công cụ ở spec.md §4.

Mỗi công cụ là một hàm Python có @tool. Docstring ghi đúng 4 ý: tên · input · output · có tác động ra ngoài không.
Khung tự ghi mỗi lần gọi công cụ vào trace. Không công cụ nào ghi dữ liệu ra ngoài: chỉ đọc CSV trong data/
và tạo bản nháp trong bộ nhớ chờ học sinh duyệt.

Dữ liệu đọc (xem data/DATA_CARD.md):
    data/question_bank.csv    ngân hàng câu hỏi (mẫu trong repo; có thể trỏ sang bản đầy đủ bằng biến môi trường BANK_CSV)
    data/student_results.csv  kết quả làm bài của học sinh mẫu HS01–HS04 (tự dựng)
"""
import csv
import json
import os
from collections import defaultdict

from tracing import tool, TOOLS  # noqa: F401  (TOOLS: danh sách công cụ đã đăng ký)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BANK_CSV = os.environ.get("BANK_CSV") or os.path.join(DATA, "question_bank.csv")
RESULTS_CSV = os.path.join(DATA, "student_results.csv")
CHAPTERS_CSV = os.path.join(DATA, "chapters.csv")

DIFFICULTIES = ("NB", "TH", "VD", "VDC")  # nhận biết, thông hiểu, vận dụng, vận dụng cao
CONFLICT_RATIO = 0.25                      # ≥ 25% câu có kết quả trái nhau trong cùng lượt → dữ liệu mâu thuẫn

_cache = {}


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_bank():
    """Các câu DÙNG ĐƯỢC của ngân hàng: đã duyệt, có chương, độ khó, đáp án và không có hình."""
    if "bank" not in _cache:
        rows = _read(BANK_CSV)
        _cache["bank"] = {
            r["ma_cau"]: r for r in rows
            if r["da_duyet"] == "true" and r["chuong"] and r["do_kho"] and r["dap_an"] and r["co_hinh"] == "false"
        }
    return _cache["bank"]


def load_chapters():
    """Chương cấp 0 trong data/chapters.csv: {mã: tên}."""
    if "chapters" not in _cache:
        _cache["chapters"] = {r["ma_chuong"]: r["ten"] for r in _read(CHAPTERS_CSV) if r["cap"] == "0"}
    return _cache["chapters"]


def _chapter_codes(row):
    return set(row["chuong"].split(";")) | set(filter(None, row["chuong_con"].split(";")))


@tool
def get_student_results(student_id: str) -> dict:
    """get_student_results · Input: mã học sinh (vd "HS01"). Output: {"found", "chapters": [{"chuong", "dung", "tong",
    "ti_le_dung"}] xếp từ yếu đến mạnh, "mau_thuan", "ti_le_cau_trai_nhau"}; "found" = False nếu chưa có lịch sử.
    Không tác động ra ngoài (chỉ đọc)."""
    rows = [r for r in _read(RESULTS_CSV) if r["ma_hs"] == student_id]
    if not rows:
        return {"student_id": student_id, "found": False, "chapters": [], "mau_thuan": False, "ti_le_cau_trai_nhau": 0.0}
    stat = defaultdict(lambda: [0, 0])
    seen = defaultdict(set)
    for r in rows:
        stat[r["chuong"]][1] += 1
        stat[r["chuong"]][0] += r["ket_qua"] == "dung"
        seen[(r["luot"], r["ma_cau"])].add(r["ket_qua"])
    chapters = [{"chuong": c, "dung": d, "tong": t, "ti_le_dung": round(d / t, 3)} for c, (d, t) in stat.items()]
    chapters.sort(key=lambda x: (x["ti_le_dung"], x["chuong"]))
    conflict = sum(1 for s in seen.values() if len(s) > 1) / len(seen)
    return {"student_id": student_id, "found": True, "chapters": chapters,
            "mau_thuan": conflict >= CONFLICT_RATIO, "ti_le_cau_trai_nhau": round(conflict, 3)}


@tool
def search_question_bank(chapter: str, difficulty: str = "", n: int = 5, exclude: tuple = ()) -> dict:
    """search_question_bank · Input: mã chương (vd "12C1"), độ khó ("NB"/"TH"/"VD"/"VDC", rỗng = mọi mức), số câu n,
    exclude = mã câu đã chọn. Output: {"ma_cau": [tối đa n mã], "co_san": số câu thoả điều kiện, "thieu": số câu còn
    thiếu so với n}; chỉ trả câu dùng được trong ngân hàng, không trả nội dung hay đáp án. Không tác động ra ngoài."""
    pool = sorted(
        q for q, r in load_bank().items()
        if chapter in _chapter_codes(r) and (not difficulty or r["do_kho"] == difficulty) and q not in exclude
    )
    picked = pool[:max(n, 0)]
    return {"chapter": chapter, "difficulty": difficulty, "yeu_cau": n, "ma_cau": picked,
            "co_san": len(pool), "thieu": max(n - len(picked), 0)}


@tool
def build_exam_draft(structure: dict, question_ids: list) -> dict:
    """build_exam_draft · Input: cấu trúc đã xác nhận (dict, chỉ để ghi lại), danh sách mã câu. Output: bản nháp
    {"trang_thai": "NHAP", "cau": [{"stt", "ma_cau", "chuong", "do_kho", "loai", "noi_dung", "lua_chon"}],
    "ma_cau_khong_hop_le"}; mã không có trong ngân hàng bị loại và báo lại; KHÔNG kèm đáp án.
    Không tác động ra ngoài: chỉ tạo bản nháp chờ học sinh duyệt."""
    bank = load_bank()
    cau, bad = [], []
    for q in question_ids:
        r = bank.get(q)
        if r is None:
            bad.append(q)
            continue
        choices = [{"nhan": c["nhan"], "noi_dung": c["noi_dung"]} for c in json.loads(r["lua_chon"] or "[]")]
        cau.append({"stt": len(cau) + 1, "ma_cau": q, "chuong": r["chuong"], "do_kho": r["do_kho"],
                    "loai": r["loai"], "noi_dung": r["noi_dung"], "lua_chon": choices})
    return {"trang_thai": "NHAP", "ghi_chu": "Bản nháp, chưa chính thức, chờ học sinh duyệt.",
            "cau_truc": structure, "cau": cau, "ma_cau_khong_hop_le": bad}


@tool
def get_exam_template(exam_code: str) -> dict:
    """get_exam_template (nhánh kỳ thi, chưa trong lát cắt đo) · Input: mã hoặc tên kỳ thi. Output: {"co": bool,
    "cau_truc"}. Hiện CHƯA có cấu trúc kỳ thi nào đã xác thực nguồn nên luôn trả "co": False — không bịa cấu trúc.
    Không tác động ra ngoài."""
    return {"exam_code": exam_code, "co": False, "cau_truc": None,
            "ghi_chu": "Chưa có cấu trúc đã xác thực nguồn cho kỳ thi này."}
