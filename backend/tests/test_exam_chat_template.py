"""Test nhánh "ôn theo mẫu kỳ thi" của issue #4, dùng mẫu giả theo đúng hợp đồng tra cứu của #5.

Các mẫu dưới đây là mẫu thử để kiểm luật, không phải cấu trúc đề thi chính thức.
"""
import re
from types import SimpleNamespace

import pytest

from app.service.exam_chat_sources import TemplateLookupSource
from app.usecase.exam_preview_rules import PreviewEdit
from app.usecase.exam_template_plan import TemplateConflict, apply_template_edit, describe_template, from_template
from tests.exam_chat_support import BASE, chat_client, new_session, no_answers, say

CK1_12 = {
    "template_id": 7,
    "name": "Cuối kỳ 1 lớp 12 (mẫu thử)",
    "exam_type": "CK1",
    "grade": 12,
    "version_label": "2025",
    "duration_minutes": 90,
    "source": "Ma trận thử của tổ Toán",
    "total_questions": 10,
    "status": "APPROVED",
    "sections": [
        {"order": 2, "title": "Phần II. Đúng sai", "question_type": "TRUE_FALSE", "count": 2,
         "points_per_question": 1.0, "difficulty_distribution": None, "chapter_codes": ["12C1"]},
        {"order": 1, "title": "Phần I. Trắc nghiệm", "question_type": "SINGLE_CHOICE", "count": 6,
         "points_per_question": 0.25, "difficulty_distribution": {"TH": 4, "VD": 2}, "chapter_codes": ["12C1", "12C4"]},
        {"order": 3, "title": "Phần III. Trả lời ngắn", "question_type": "SHORT_ANSWER", "count": 2,
         "points_per_question": 0.5, "difficulty_distribution": None, "chapter_codes": ["12C4"]},
    ],
}


def _thpt(template_id: int, version: str) -> dict:
    return {"template_id": template_id, "name": f"Tốt nghiệp THPT {version} (mẫu thử)", "exam_type": "THPT",
            "grade": None, "version_label": version, "duration_minutes": 90, "source": "Đề minh hoạ thử",
            "total_questions": 3, "status": "APPROVED",
            "sections": [{"order": 1, "title": "Phần I", "question_type": "SINGLE_CHOICE", "count": 3,
                          "points_per_question": None, "difficulty_distribution": None, "chapter_codes": None}]}


class FakeTemplates:
    """Nguồn mẫu giả, lọc giống GET /exam-templates/lookup của #5 (mẫu không ghi khối khớp mọi khối)."""

    def __init__(self, items: list[dict]) -> None:
        self.items = items

    async def find(self, exam_type, grade, version_label):
        return [t for t in self.items
                if t["exam_type"] == exam_type
                and (grade is None or t["grade"] in (grade, None))
                and (version_label is None or t["version_label"] == version_label)]


TEMPLATES = FakeTemplates([CK1_12, _thpt(8, "2024"), _thpt(9, "2025")])


@pytest.fixture
async def chat():
    async with chat_client(templates=TEMPLATES) as c:
        yield c


async def _template_session(chat) -> tuple[int, dict]:
    sid = await new_session(chat)
    reply, preview, draft = await say(chat, sid, "Em muốn ôn thi cuối kỳ 1 lớp 12")
    assert draft is None
    return sid, preview


# ---------- luật thuần ----------

def test_from_template_sorts_sections_and_keeps_snapshot():
    s = from_template(CK1_12)
    assert [sec.order for sec in s.sections] == [1, 2, 3]
    assert s.total == 10 and s.kind == "EXAM_TEMPLATE"
    assert s.sections[0].difficulty_plan() == {"TH": 4, "VD": 2}
    assert s.sections[1].difficulty_plan() == {None: 2}
    text = describe_template(s, {"12C1": "ỨNG DỤNG ĐẠO HÀM"})
    assert "Phần I. Trắc nghiệm: 6 câu trắc nghiệm một đáp án" in text and "Nguồn cấu trúc" in text


def test_template_edit_only_narrows_chapters():
    s = from_template(CK1_12)
    narrowed = apply_template_edit(s, PreviewEdit(chapter_codes=["12C4"]))
    assert narrowed.sections[0].effective_chapters() == ["12C4"]
    assert narrowed.sections[1].effective_chapters() == ["12C1"]   # phần không giao: giữ phạm vi gốc của mẫu
    assert s.sections[0].chapters is None                          # bản cũ không bị sửa

    for edit, fragment in [
        (PreviewEdit(total=8), "cố định 10 câu"),
        (PreviewEdit(only_difficulty="VD"), "độ khó"),
        (PreviewEdit(chapter_counts={"12C1": 5}), "số câu từng phần"),
        (PreviewEdit(chapter_codes=["11C6"]), "không nằm trong phạm vi"),
    ]:
        with pytest.raises(TemplateConflict) as e:
            apply_template_edit(s, edit)
        assert any(fragment in msg for msg in e.value.errors), e.value.errors


def test_template_edit_rejects_chapter_above_grade():
    open_scope = {**_thpt(1, "2025"), "grade": 11, "exam_type": "CK1"}
    with pytest.raises(TemplateConflict) as e:
        apply_template_edit(from_template(open_scope), PreviewEdit(chapter_codes=["12C1"]))
    assert "vượt khối 11" in e.value.errors[0]


async def test_lookup_adapter_filters_non_approved():
    orm_like = [SimpleNamespace(**CK1_12), SimpleNamespace(**{**CK1_12, "template_id": 99, "status": "DRAFT"})]

    async def lookup(*, exam_type, grade, version_label):
        assert (exam_type, grade, version_label) == ("CK1", 12, None)
        return orm_like

    found = await TemplateLookupSource(lookup).find("CK1", 12, None)
    assert [t["template_id"] for t in found] == [7]
    assert found[0]["sections"] == CK1_12["sections"]


# ---------- qua API ----------

async def test_single_template_becomes_preview(chat):
    sid, preview = await _template_session(chat)
    assert preview["mode"] == "EXAM_TEMPLATE" and preview["status"] == "PROPOSED"
    structure = preview["structure"]
    assert structure["kind"] == "EXAM_TEMPLATE" and structure["template_id"] == 7
    assert [s["title"] for s in structure["sections"]] == ["Phần I. Trắc nghiệm", "Phần II. Đúng sai",
                                                          "Phần III. Trả lời ngắn"]
    state = (await chat.get(f"{BASE}/sessions/{sid}")).json()
    assert "Phần I. Trắc nghiệm" in state["messages"][-1]["content"]
    assert not re.search(r"Q\d{5}", state["messages"][-1]["content"])   # chưa có câu trước khi xác nhận


async def test_confirm_builds_draft_by_section_type_and_reports_shortage(chat):
    sid, _ = await _template_session(chat)
    reply, preview, draft = await say(chat, sid, "Em xác nhận, tạo đề")
    assert preview["status"] == "BUILT"
    assert draft["title"].startswith("Đề ôn luyện ngày")
    assert draft["structure"]["kind"] == "EXAM_TEMPLATE"

    by_section = {}
    for item in draft["items"]:
        by_section.setdefault(item["section_title"], []).append(item)
    assert [i["code"] for i in by_section["Phần I. Trắc nghiệm"]] == ["Q00001", "Q00002", "Q00003", "Q00004",
                                                                     "Q00005", "Q00006"]
    assert {i["type"] for i in by_section["Phần I. Trắc nghiệm"]} == {"SINGLE_CHOICE"}
    assert [i["code"] for i in by_section["Phần II. Đúng sai"]] == ["Q00040", "Q00041"]
    assert {i["type"] for i in by_section["Phần II. Đúng sai"]} == {"TRUE_FALSE"}
    assert [i["code"] for i in by_section["Phần III. Trả lời ngắn"]] == ["Q00050"]   # ngân hàng chỉ có 1 câu
    assert by_section["Phần I. Trắc nghiệm"][0]["points"] == 0.25
    assert by_section["Phần I. Trắc nghiệm"][0]["chapter"] == "12C1"                  # chương gốc của câu
    assert "Q00011" not in reply and "Q00043" not in reply                            # câu chưa duyệt bị loại

    [shortage] = draft["shortages"]
    assert shortage["section_title"] == "Phần III. Trả lời ngắn"
    assert shortage["question_type"] == "SHORT_ANSWER"
    assert (shortage["requested"], shortage["available"]) == (2, 1)
    assert "9/10 câu" in reply and "không tự bịa" in reply
    no_answers(draft)


async def test_conflicting_edits_are_refused_by_chat_and_api(chat):
    sid, preview = await _template_session(chat)

    reply, changed, _ = await say(chat, sid, "giảm còn 8 câu")
    assert "xung đột với mẫu kỳ thi" in reply and "cố định 10 câu" in reply
    assert changed is None
    assert (await chat.get(f"{BASE}/sessions/{sid}/preview")).json()["version"] == preview["version"]

    r = await chat.patch(f"{BASE}/sessions/{sid}/preview",
                         json={"version": preview["version"], "edit": {"only_difficulty": "VD"}})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "TEMPLATE_CONFLICT"

    r = await chat.patch(f"{BASE}/sessions/{sid}/preview",
                         json={"version": preview["version"], "edit": {"chapter_codes": ["11C6"]}})
    assert r.status_code == 422 and "không nằm trong phạm vi" in r.json()["detail"]["errors"][0]


async def test_narrowing_via_api_is_used_by_next_chat_confirm(chat):
    sid, preview = await _template_session(chat)
    r = await chat.patch(f"{BASE}/sessions/{sid}/preview",
                         json={"version": preview["version"], "edit": {"chapter_codes": ["12C4"]}})
    assert r.status_code == 200 and r.json()["status"] == "EDITED"
    assert r.json()["structure"]["sections"][0]["chapters"] == ["12C4"]

    _, _, draft = await say(chat, sid, "xác nhận")
    first = [i for i in draft["items"] if i["section_title"] == "Phần I. Trắc nghiệm"]
    # 12C4 chỉ có 3 TH + 1 VD + 1 NB. Ô thiếu bù cùng chương trước (Q00024), hết mới sang chương khác cùng mức (Q00005).
    assert [(i["code"], i["chapter"], i["difficulty"]) for i in first] == [
        ("Q00020", "12C4", "TH"), ("Q00021", "12C4", "TH"), ("Q00022", "12C4", "TH"),
        ("Q00024", "12C4", "NB"), ("Q00023", "12C4", "VD"), ("Q00005", "12C1", "VD")]
    assert all(s["section_title"] != "Phần I. Trắc nghiệm" for s in draft["shortages"])


async def test_confirm_via_api_in_template_mode(chat):
    sid, preview = await _template_session(chat)
    r = await chat.post(f"{BASE}/sessions/{sid}/preview/confirm", json={"version": preview["version"]})
    assert r.status_code == 200
    assert r.json()["draft"]["structure"]["template_id"] == 7
    assert len(r.json()["draft"]["items"]) == 9


async def test_several_templates_ask_back_then_year_picks_one(chat):
    sid = await new_session(chat)
    reply, preview, _ = await say(chat, sid, "Em muốn ôn theo đề thi tốt nghiệp THPT")
    assert preview is None
    assert "Có 2 mẫu đã duyệt" in reply and "2024" in reply and "2025" in reply

    reply, preview, _ = await say(chat, sid, "Ôn theo đề thi tốt nghiệp THPT 2025")
    assert preview["structure"]["template_id"] == 9


async def test_missing_exam_type_or_unknown_template(chat):
    sid = await new_session(chat)
    reply, preview, _ = await say(chat, sid, "Em muốn ôn thi cuối kỳ lớp 12")
    assert "kỳ thi nào" in reply and preview is None
    reply, preview, _ = await say(chat, sid, "Em muốn ôn thi giữa kỳ 2 lớp 10")
    assert "chưa có cấu trúc đã xác thực" in reply and preview is None


async def test_student_can_switch_back_to_chapter_mode(chat):
    sid, _ = await _template_session(chat)
    _, preview, _ = await say(chat, sid, "Thôi em ôn theo chương 12C4, 6 câu")
    assert preview["mode"] == "CHAPTER"
    assert preview["structure"]["chapters"] == [{"code": "12C4", "count": 6}]
