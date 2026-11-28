"""Test đối chiếu: backend (#4) và bản chạy thử codebase/agent.py phải cư xử giống nhau trên 13 câu thử.

Vì sao cần: image Docker của backend chỉ chứa thư mục backend/, nên logic agent được viết lại trong backend. Từ đó
có hai bản logic: codebase/ (lát cắt được chấm qua eval/benchmark.csv) và backend/ (sản phẩm). Test này chạy cùng
một câu thử qua cả hai, trên cùng dữ liệu, và báo khi hai bên khác nhau.

Cách làm:
- Bản chạy thử chạy ở chế độ model giả (MODEL_PROVIDER=fake), đọc data/*.csv như bình thường.
- Backend dùng SQLite nạp từ chính các file CSV đó: câu "dùng được" theo luật của codebase/tools.py được đánh dấu
  PUBLISHED, lịch sử làm bài tính giống get_student_results().
- So "hành vi", không so nguyên văn: loại kết quả (từ chối, hỏi lại, đề xuất cấu trúc, đề nháp...), từng dòng cấu
  trúc (chương, số câu, phân bố độ khó) và đúng tập mã câu của đề nháp.

Chỉ đọc eval/benchmark.csv và data/*.csv; không sửa gì trong codebase/, eval/ hay data/.
Bỏ qua (skip) nếu không có các thư mục đó, ví dụ khi chạy trong image Docker chỉ chứa backend/.
"""
import csv
import importlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest
from sqlalchemy import insert

from app.repositories.question_bank_repository import chapters, questions, questions_chapters
from app.service.exam_chat_sources import ChapterResult, StaticHistory, StudentHistory
from tests.exam_chat_support import chat_client, new_session, say

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
BENCH = REPO / "eval" / "benchmark.csv"
CODEBASE = REPO / "codebase"

pytestmark = pytest.mark.skipif(
    not (CODEBASE / "agent.py").exists() or not BENCH.exists() or not (DATA / "question_bank.csv").exists(),
    reason="cần codebase/, eval/benchmark.csv và data/*.csv (chạy từ repo đầy đủ)",
)


def _read(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _cases() -> list[dict]:
    if not BENCH.exists():
        return []
    with open(BENCH, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------- bản chạy thử (codebase/) ----------

@pytest.fixture(scope="module")
def agent():
    """Nạp codebase/agent.py ở chế độ model giả. Biến môi trường thắng .env (load_env dùng setdefault)."""
    old_env = os.environ.get("MODEL_PROVIDER")
    os.environ["MODEL_PROVIDER"] = "fake"
    sys.path.insert(0, str(CODEBASE))
    try:
        # codebase/ dùng tên module chung (ai, tools, agent, tracing): nạp mới và gỡ ra sau khi xong.
        for name in ("tracing", "ai", "tools", "agent"):
            sys.modules.pop(name, None)
        module = importlib.import_module("agent")
        yield module
    finally:
        for name in ("tracing", "ai", "tools", "agent"):
            sys.modules.pop(name, None)
        sys.path.remove(str(CODEBASE))
        if old_env is None:
            os.environ.pop("MODEL_PROVIDER", None)
        else:
            os.environ["MODEL_PROVIDER"] = old_env


# ---------- backend: cùng dữ liệu, nạp vào SQLite ----------

def _usable(row: dict) -> bool:
    """Đúng luật load_bank() của codebase/tools.py."""
    return (row["da_duyet"] == "true" and bool(row["chuong"]) and bool(row["do_kho"]) and bool(row["dap_an"])
            and row["co_hinh"] == "false")


async def _seed_from_csv(conn) -> None:
    chapter_rows = _read("chapters.csv")
    ids = {r["ma_chuong"]: i for i, r in enumerate(chapter_rows, start=1)}
    await conn.execute(insert(chapters), [
        {"chapter_id": ids[r["ma_chuong"]], "code": r["ma_chuong"], "name": r["ten"],
         "parent_chapter_id": ids.get(r["ma_chuong_cha"]) if r["ma_chuong_cha"] else None, "level": int(r["cap"])}
        for r in chapter_rows
    ])
    q_rows, links = [], []
    for r in _read("question_bank.csv"):
        qid = int(r["ma_cau"][1:])
        q_rows.append({"question_id": qid, "content": r["noi_dung"], "type": r["loai"],
                       "difficulty": r["do_kho"] or None, "grade": int(r["lop"]) if r["lop"] else None,
                       "visibility": "PUBLISHED" if _usable(r) else "DRAFT"})
        codes = set(filter(None, r["chuong"].split(";"))) | set(filter(None, r["chuong_con"].split(";")))
        links += [{"question_id": qid, "chapter_id": ids[c]} for c in sorted(codes) if c in ids]
    await conn.execute(insert(questions), q_rows)
    await conn.execute(insert(questions_chapters), links)


def _history_from_csv() -> StaticHistory:
    """Đúng cách tính của get_student_results() trong codebase/tools.py."""
    stat: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    seen: dict[str, dict[tuple, set]] = defaultdict(lambda: defaultdict(set))
    for r in _read("student_results.csv"):
        cell = stat[r["ma_hs"]][r["chuong"]]
        cell[1] += 1
        cell[0] += r["ket_qua"] == "dung"
        seen[r["ma_hs"]][(r["luot"], r["ma_cau"])].add(r["ket_qua"])
    out = {}
    for sid, per_chapter in stat.items():
        pairs = seen[sid]
        conflict = sum(1 for s in pairs.values() if len(s) > 1) / len(pairs)
        out[sid] = StudentHistory([ChapterResult(c, d, t) for c, (d, t) in per_chapter.items()],
                                  conflict_ratio=round(conflict, 3))
    return StaticHistory(out)


# ---------- so hành vi ----------

PREVIEW_LINE = re.compile(r"^- (1[0-2]C\d+)\b[^:\n]*: (\d+) câu \(([^)]*)\)", re.M)
CATEGORIES = [
    ("từ chối", re.compile(r"không thể|không đưa đáp án|chỉ hỗ trợ ôn môn Toán")),
    ("chưa có lịch sử", re.compile(r"chưa có lịch sử")),
    ("mâu thuẫn", re.compile(r"mâu thuẫn")),
    ("chưa có mẫu kỳ thi", re.compile(r"chưa có cấu trúc đã xác thực")),
    ("chương không có", re.compile(r"chưa có câu hỏi về chương")),
]


def behaviour(text: str) -> dict:
    codes = sorted(set(re.findall(r"Q\d{5}", text)))
    if codes:
        return {"loại": "đề nháp", "mã câu": codes, "báo thiếu": "không đủ câu" in text}
    if "Đề xuất cấu trúc" in text:
        return {"loại": "đề xuất cấu trúc", "dòng": PREVIEW_LINE.findall(text)}
    for name, pattern in CATEGORIES:
        if pattern.search(text):
            return {"loại": name}
    return {"loại": "hỏi lại"}


# Backend bù câu thiếu bằng câu thật cùng chương khác mức, hoặc cùng mức khác chương, thay vì chỉ báo thiếu như bản
# chạy thử. Ba câu thử đo đúng ca "ngân hàng thiếu câu" nên lệch có chủ đích; đưa bản chạy thử về cùng hành vi là
# quyết định của nhóm (đụng chuẩn đạt ở eval/benchmark.csv). strict=True: khi hai bên khớp lại, test báo để gỡ dòng này.
BACKFILL_DIVERGENCE = {"B08", "B19", "B22"}


def _params():
    return [pytest.param(c, id=c["id"], marks=pytest.mark.xfail(
        c["id"] in BACKFILL_DIVERGENCE, strict=True, reason="backend bù câu thiếu, bản chạy thử báo thiếu"))
        for c in _cases()]


@pytest.mark.parametrize("case", _params())
async def test_backend_matches_codebase_agent(agent, case):
    text = case["input"]
    expected = behaviour(agent.answer(text)["output"])

    m = re.search(r"\b(HS\d+)\b", text, re.I)
    async with chat_client(history=_history_from_csv(), seed_fn=_seed_from_csv) as c:
        sid = await new_session(c, m.group(1).upper() if m else "HS00")
        reply, _, _ = await say(c, sid, text)
    actual = behaviour(reply)

    assert actual == expected, f"{case['id']} lệch hành vi\n  codebase: {expected}\n  backend:  {actual}\n  backend trả: {reply[:400]}"
