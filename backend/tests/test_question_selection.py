"""Chọn câu: ngẫu nhiên, tránh câu đã làm ("ôn tiếp") và ôn lại câu đã sai. Dữ liệu thử tự dựng, không phải dữ liệu thật."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.repositories import question_bank_repository as bank_module
from app.repositories.question_bank_repository import QuestionBankRepository
from app.service.exam_chat_model import (
    ChatAction,
    ExamChatModel,
    PracticeRecommendation,
)
from app.service.exam_chat_sources import (
    ChapterResult,
    QuestionRecord,
    StaticHistory,
    StudentHistory,
)
from app.usecase import exam_chat_intent as intent
from app.usecase.exam_preview_rules import (
    ChapterCount,
    PreviewEdit,
    PreviewStructure,
    apply_edit,
    check_structure,
)
from app.usecase.exam_review import PickPolicy, rank_wrong
from app.usecase.study_stats import GradedAttempt, question_records
from tests.exam_chat_support import chat_client, login_as, new_session, say
from tests.test_live_exam_chat import PROFILE, confirm, live  # noqa: F401  (fixture `live`)

REAL_SHUFFLE = bank_module.shuffle_candidates   # lấy lúc import, trước khi fixture tự động thay bằng bản giữ thứ tự
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
SC = "SINGLE_CHOICE"


def codes(draft: dict) -> list[str]:
    return [item["code"] for item in draft["items"]]


# ---------- tầng kho câu hỏi: ngẫu nhiên, ưu tiên, loại trừ ----------


async def test_pick_shuffles_within_tier_and_real_shuffle_varies(monkeypatch):
    async with chat_client() as client, client.db() as session:
        bank = QuestionBankRepository(session)
        args = dict(question_type=SC, chapter_codes=["12C4"], difficulty="TH")
        assert (await bank.pick_for_section(n=3, **args)).question_ids == [20, 21, 22]   # fixture: giữ thứ tự mã
        monkeypatch.setattr(bank_module, "shuffle_candidates", lambda ids: ids[::-1])
        assert (await bank.pick_for_section(n=2, **args)).question_ids == [22, 21]
        monkeypatch.setattr(bank_module, "shuffle_candidates", REAL_SHUFFLE)
        seen = {tuple((await bank.pick_for_section(n=1, **args)).question_ids) for _ in range(60)}
        assert len(seen) > 1 and seen <= {(20,), (21,), (22,)}


async def test_subchapter_preference_comes_before_random(monkeypatch):
    monkeypatch.setattr(bank_module, "shuffle_candidates", lambda ids: ids[::-1])
    async with chat_client() as client, client.db() as session:
        bank = QuestionBankRepository(session)
        result = await bank.pick_for_section(question_type=SC, n=5, chapter_codes=["12C1"], prefer_subchapters=True)
        assert result.question_ids[:4] == [4, 3, 2, 1]        # câu gắn chương con 12C11 trước, xáo trong cùng nhóm
        assert set(result.question_ids[4:]) <= {5, 6, 7, 8, 9, 10}


async def test_priority_only_and_exclude_filter_the_pool(monkeypatch):
    monkeypatch.setattr(bank_module, "shuffle_candidates", lambda ids: ids[::-1])
    async with chat_client() as client, client.db() as session:
        bank = QuestionBankRepository(session)
        args = dict(question_type=SC, chapter_codes=["12C4"], difficulty="TH")
        ranked = await bank.pick_for_section(n=3, only={20, 21, 22}, priority={21: 3, 22: 1}, **args)
        assert ranked.question_ids == [21, 22, 20]             # điểm cao trước, câu không điểm cuối
        only = await bank.pick_for_section(n=3, only={20}, **args)
        assert only.question_ids == [20] and only.available == 1
        excluded = await bank.pick_for_section(n=3, exclude=[21], **args)
        assert 21 not in excluded.question_ids and excluded.available == 2


async def test_practice_capacity_and_cells_respect_exclusion_and_scope():
    async with chat_client() as client, client.db() as session:
        bank = QuestionBankRepository(session)
        full, total = await bank.practice_capacity(["12C4"], ["TH"], [SC])
        fewer, remaining = await bank.practice_capacity(["12C4"], ["TH"], [SC], exclude={20, 21})
        assert (total, remaining) == (3, 1) and fewer[0]["available"] == 1 and full[0]["available"] == 3
        cells = await bank.question_cells([1, 5, 11, 20, 30], ["12C1", "12C4"])
        assert cells == {1: ("12C11", "TH", SC), 5: ("12C1", "VD", SC), 20: ("12C4", "TH", SC)}   # 11 nháp, 30 ngoài phạm vi


# ---------- lịch sử theo câu và luật ----------


def attempt(statuses: dict, *, when=T0, conflicts=()) -> GradedAttempt:
    items = [{"code": code, "question_id": int(code[1:])} for code in statuses]
    return GradedAttempt(attempt_id=1, draft_id=1, title="t", started_at=when, finished_at=when, duration_minutes=0,
                         score=0.0, reason=None, items=items, statuses=statuses, conflicts=set(conflicts),
                         graded_at=when)


def test_question_records_count_done_and_wrong():
    later = T0 + timedelta(days=1)
    records = question_records([
        attempt({"Q00001": "wrong", "Q00002": "correct", "Q00003": "skipped", "Q00004": "wrong"}, when=later,
                conflicts={"Q00004"}),
        attempt({"Q00001": "partial", "Q00002": "wrong"}),
    ])
    assert records[1] == QuestionRecord(1, done=2, wrong=2, last_wrong_at=later)
    assert records[2] == QuestionRecord(2, done=2, wrong=1, last_wrong_at=T0)
    assert 3 not in records and 4 not in records         # bỏ qua và mâu thuẫn không tính là đã làm


def test_rank_wrong_orders_by_wrong_count_then_recency():
    ranked = rank_wrong([
        QuestionRecord(1, 3, 1, T0), QuestionRecord(2, 5, 3, T0), QuestionRecord(3, 2, 1, T0 + timedelta(days=2)),
        QuestionRecord(4, 9, 0), QuestionRecord(5, 2, 2, T0),
    ])
    assert [r.question_id for r in ranked] == [2, 5, 3, 1]


def test_policy_follows_structure_flags():
    records = {1: QuestionRecord(1, 2, 0), 2: QuestionRecord(2, 3, 2, T0), 3: QuestionRecord(3, 1, 1, T0)}
    base = PreviewStructure(chapters=[ChapterCount(code="12C1", count=3)])
    assert not PickPolicy.for_structure(base, records).active
    avoid = PickPolicy.for_structure(base.model_copy(update={"avoid_repeats": True}), records)
    assert avoid.avoid == {1, 2, 3} and avoid.only is None
    wrong = PickPolicy.for_structure(base.model_copy(update={"review_wrong": True}), records)
    assert wrong.only == {2, 3} and wrong.avoid == frozenset() and wrong.priority == {2: 2, 3: 1}


def test_flags_are_exclusive_and_editable():
    both = PreviewStructure(chapters=[ChapterCount(code="12C1", count=3)], avoid_repeats=True, review_wrong=True)
    assert any("ôn lại câu sai" in error for error in check_structure(both))
    base = PreviewStructure(chapters=[ChapterCount(code="12C1", count=3)], avoid_repeats=True)
    assert apply_edit(base, PreviewEdit(avoid_repeats=False)).avoid_repeats is False
    assert apply_edit(base, PreviewEdit(total=6)).avoid_repeats is True      # chỉnh khác giữ nguyên cờ


@pytest.mark.parametrize("text, kind", [
    ("Ôn lại câu sai", "wrong"), ("Làm lại các câu em đã sai", "wrong"), ("Ra đề 5 câu sai nhiều lần", "wrong"),
    ("Ra đề ôn chương em hay sai", "weak"), ("Ôn các câu em hay sai", "weak"), ("Tạo đề ôn tiếp", "weak"),
    ("Ra đề 10 câu về chương em hay sai", "weak"),
])
def test_intent_separates_wrong_questions_from_weak_chapters(text, kind):
    assert intent.read(text).kind == kind


def test_intent_reads_repeat_flag_and_counts():
    assert intent.read("Ôn lại 4 câu sai chương 12C1").edit.total == 4
    assert intent.read("Ôn lại 4 câu sai chương 12C1").edit.chapter_codes == ["12C1"]
    assert intent.parse_edit(intent.norm("cho phép làm lại câu đã làm")).avoid_repeats is False
    assert intent.parse_edit(intent.norm("đừng lặp lại câu cũ")).avoid_repeats is True
    assert intent.parse_edit(intent.norm("giảm còn 4 câu")).avoid_repeats is None


# ---------- luồng chat theo quy tắc (không cần model) ----------

DONE = [QuestionRecord(q, 1, 0) for q in (1, 2, 3, 5, 6, 8)]
WRONG = [
    QuestionRecord(3, 4, 3, T0), QuestionRecord(1, 2, 2, T0), QuestionRecord(5, 3, 1, T0),
    QuestionRecord(20, 1, 1, T0 + timedelta(days=1)), QuestionRecord(2, 5, 0),
]
RULE_HISTORY = StaticHistory(
    {"HS05": StudentHistory([ChapterResult("12C1", 2, 10)]), "HS06": StudentHistory([ChapterResult("12C1", 2, 10)]),
     "HS07": StudentHistory([ChapterResult("12C1", 2, 10)])},
    records={"HS05": DONE, "HS06": WRONG},
)


@pytest.fixture
async def chat():
    async with chat_client(history=RULE_HISTORY) as client:
        yield client


async def test_next_practice_avoids_done_questions_by_default_and_can_opt_out(chat):
    sid = await new_session(chat, "HS05")
    reply, preview, _ = await say(chat, sid, "Tạo đề ôn tiếp 4 câu")
    assert preview["structure"]["avoid_repeats"] is True and "Không lấy lại câu em đã làm" in reply
    _, _, draft = await say(chat, sid, "Em xác nhận, tạo đề nháp")
    done = {f"Q{q.question_id:05d}" for q in DONE}
    assert len(draft["items"]) == 4 and not done & set(codes(draft))

    other = await new_session(chat, "HS05")
    await say(chat, other, "Tạo đề ôn tiếp 4 câu")
    _, preview, _ = await say(chat, other, "Cho phép làm lại câu đã làm")
    assert preview["structure"]["avoid_repeats"] is False
    _, _, draft = await say(chat, other, "Em xác nhận, tạo đề nháp")
    assert done & set(codes(draft))                       # tắt cờ thì câu đã làm được lấy lại


async def test_avoid_repeats_without_history_keeps_old_behaviour(chat):
    sid = await new_session(chat, "HS07")
    _, preview, _ = await say(chat, sid, "Tạo đề ôn tiếp 3 câu")
    assert preview["structure"]["avoid_repeats"] is True
    _, _, draft = await say(chat, sid, "Em xác nhận, tạo đề nháp")
    assert len(draft["items"]) == 3                       # chưa làm câu nào: không có gì để loại


async def test_review_wrong_picks_only_wrong_questions_most_wrong_first(chat):
    sid = await new_session(chat, "HS06")
    reply, preview, _ = await say(chat, sid, "Ôn lại 3 câu sai")
    structure = preview["structure"]
    assert structure["review_wrong"] is True and structure["avoid_repeats"] is False
    assert sum(c["count"] for c in structure["chapters"]) == 3 and "nhiều nhất sai 3 lần" in reply
    assert "câu em từng làm sai" in reply and "chương em hay sai" not in reply
    _, _, draft = await say(chat, sid, "Em xác nhận, tạo đề nháp")
    # sai 3 lần (Q3), sai 2 lần (Q1), rồi trong hai câu sai 1 lần thì Q20 sai gần hơn Q5. Q2 làm đúng nên bị loại.
    assert codes(draft) == ["Q00003", "Q00001", "Q00020"]


async def test_review_wrong_is_shorter_when_few_wrong_and_stops_when_none(chat):
    sid = await new_session(chat, "HS06")
    reply, preview, _ = await say(chat, sid, "Ôn lại 10 câu sai")
    assert sum(c["count"] for c in preview["structure"]["chapters"]) == 4 and "ngắn hơn 10 câu" in reply
    none = await new_session(chat, "HS07")
    reply, preview, _ = await say(chat, none, "Ôn lại câu sai")
    assert preview is None and "chưa thấy câu nào em làm sai" in reply


async def test_review_wrong_can_be_limited_to_a_chapter(chat):
    sid = await new_session(chat, "HS06")
    _, preview, _ = await say(chat, sid, "Ôn lại câu sai chương 12C4")
    assert preview["structure"]["chapters"] == [{"code": "12C4", "count": 1}]
    _, _, draft = await say(chat, sid, "Em xác nhận, tạo đề nháp")
    assert codes(draft) == ["Q00020"]


async def test_weak_chapter_request_is_not_review_wrong(chat):
    sid = await new_session(chat, "HS06")
    _, preview, _ = await say(chat, sid, "Ra đề ôn chương em hay sai.")
    assert preview["structure"]["review_wrong"] is False


# ---------- luồng live (model giả) ----------


class AnyHistory:
    """Cùng một lịch sử cho mọi học sinh đăng nhập (mã học sinh sinh theo user_id)."""

    def __init__(self, records: list[QuestionRecord]) -> None:
        self.records = records

    async def get(self, student_ref, *, grade=None, chapter_codes=()):
        rows = [ChapterResult("12C1", 2, 10), ChapterResult("12C4", 6, 10)]
        zero = [ChapterResult(row.code, 0, 0) for row in rows]
        return StudentHistory(rows, latest=zero, earlier=zero, attempt_count=1)

    async def questions(self, student_ref):
        return {r.question_id: r for r in self.records}


def plan(count=2):
    return PracticeRecommendation.model_validate({"groups": [{
        "chapter_code": "12C11", "type": SC, "difficulty": "TH", "count": count, "evidence_ref": "12C1",
        "rationale": "reinforce_basics",
    }]})


async def set_profile(client):
    result = await client.put(PROFILE, json={"school_name": "THPT Mẫu", "grade": 12, "target_score": 8,
                                             "exam_period": "final_1", "study_days": [1, 3]})
    assert result.status_code == 200


@pytest.fixture
def recommend(monkeypatch):
    mock = AsyncMock(return_value=plan())
    monkeypatch.setattr(ExamChatModel, "recommend", lambda _self, context: mock(context))
    return mock


async def test_live_history_avoids_done_by_default_and_explains(live, recommend):
    live.return_value = ChatAction(action="history", total=2)
    async with chat_client(real_auth=True, history=AnyHistory([QuestionRecord(1, 2, 0)])) as client:
        await login_as(client, "avoid-live@example.com")
        await set_profile(client)
        sid = await new_session(client, None)
        reply, preview, _ = await say(client, sid, "Gợi ý bài em nên làm tiếp")
        assert preview["structure"]["avoid_repeats"] is True and "bỏ 1 câu em đã làm" in reply
        built = (await confirm(client, sid, preview["version"])).json()["draft"]
        assert len(built["items"]) == 2 and "Q00001" not in codes(built)
        bank = recommend.call_args.args[0]["bank"]
        assert next(c for c in bank if c["chapter_code"] == "12C11")["available"] == 3   # 4 câu TH trừ câu đã làm


async def test_live_history_allow_repeats_flag_keeps_done_questions(live, recommend):
    live.return_value = ChatAction(action="history", total=2, avoid_repeats=False)
    async with chat_client(real_auth=True, history=AnyHistory([QuestionRecord(1, 2, 0)])) as client:
        await login_as(client, "repeat-live@example.com")
        await set_profile(client)
        sid = await new_session(client, None)
        _, preview, _ = await say(client, sid, "Ôn tiếp, cho phép làm lại câu cũ")
        assert preview["structure"]["avoid_repeats"] is False
        built = (await confirm(client, sid, preview["version"])).json()["draft"]
        assert "Q00001" in codes(built)


async def test_live_history_reports_when_fresh_questions_run_out(live, recommend):
    live.return_value = ChatAction(action="history", total=2)
    done = [QuestionRecord(q, 1, 0) for q in (1, 2, 3, 4, 20, 21, 22, 23, 24)]   # hết câu 12C11 và 12C4 chưa làm
    async with chat_client(real_auth=True, history=AnyHistory(done)) as client:
        await login_as(client, "short-live@example.com")
        await set_profile(client)
        sid = await new_session(client, None)
        reply, preview, _ = await say(client, sid, "Gợi ý bài em nên làm tiếp")
        assert preview is None and "0/2 câu chưa làm" in reply
        assert "cho phép làm lại câu đã làm" in reply and "ôn lại câu sai" in reply   # gợi ý hai lối thoát
        recommend.assert_not_awaited()                              # không hỏi model khi kho không đủ câu mới


async def test_live_history_rejects_plan_larger_than_fresh_capacity(live, recommend):
    live.return_value = ChatAction(action="history", total=2)
    recommend.return_value = plan(count=2)                          # ô 12C11 TH chỉ còn 1 câu chưa làm
    async with chat_client(real_auth=True, history=AnyHistory([QuestionRecord(q, 1, 0) for q in (1, 2, 3)])) as client:
        await login_as(client, "plan-live@example.com")
        await set_profile(client)
        sid = await new_session(client, None)
        reply, preview, _ = await say(client, sid, "Gợi ý bài em nên làm tiếp")
        assert preview is None and "vượt số câu hiện có" in reply


async def test_live_review_wrong_shortcut_and_replacement_stay_inside_wrong_set(live, recommend):
    wrong = [QuestionRecord(2, 3, 3, T0), QuestionRecord(3, 2, 2, T0), QuestionRecord(4, 2, 1, T0),
             QuestionRecord(1, 5, 0)]
    async with chat_client(real_auth=True, history=AnyHistory(wrong)) as client:
        await login_as(client, "wrong-live@example.com")
        await set_profile(client)
        sid = await new_session(client, None)
        reply, preview, _ = await say(client, sid, "Ôn lại 2 câu sai")
        live.assert_not_awaited()                                    # nhận diện bằng quy tắc, không gọi model
        assert preview["structure"]["review_wrong"] is True and preview["reason"] == "Ôn lại các câu đã làm sai."
        built = (await confirm(client, sid, preview["version"])).json()["draft"]
        assert codes(built) == ["Q00002", "Q00003"]                  # sai nhiều lần nhất; Q1 làm đúng nên không có
        live.return_value = ChatAction(action="replace", question_orders=[2])
        _, preview, _ = await say(client, sid, "Đổi câu thứ hai")
        changed = (await confirm(client, sid, preview["version"])).json()["draft"]
        assert codes(changed) == ["Q00002", "Q00004"]                # câu thay thế vẫn là câu từng sai


async def test_live_shortage_offer_can_be_accepted_with_random_picks(live, monkeypatch):
    """Câu chọn ngẫu nhiên nên mỗi lần dựng ra bộ ID khác; xác nhận đề rút gọn vẫn phải thành công."""
    monkeypatch.setattr(bank_module, "shuffle_candidates", REAL_SHUFFLE)
    live.return_value = ChatAction(action="chapter", chapters=["12C1"], total=8, difficulty_counts={"TH": 8})
    async with chat_client(real_auth=True) as client:
        await login_as(client, "random-live@example.com")
        await client.put(PROFILE, json={"school_name": "THPT Mẫu", "grade": 11, "target_score": 8,
                                        "exam_period": "final_1", "study_days": [1, 3]})
        sid = await new_session(client, None)
        _, preview, _ = await say(client, sid, "Ôn chương ứng dụng đạo hàm")
        first = (await confirm(client, sid, preview["version"])).json()
        count = first["preview"]["offer"]["count"]
        assert first["draft"] is None and count == 7
        accepted = (await confirm(client, sid, first["preview"]["version"], count)).json()
        assert accepted["draft"] is not None and len(accepted["draft"]["items"]) == count
