"""Câu thiếu đáp án không được vào đề, và đề cũ lẫn câu thiếu đáp án vẫn làm online được. Dữ liệu thử tự dựng."""
import pytest
from sqlalchemy import insert, text

from app.models.exam_chat import ExamChatSession, ExamDraft
from app.repositories.question_bank_repository import QuestionBankRepository, chapters, questions, questions_chapters, statements
from tests.exam_chat_support import chat_client, login_as
from tests.test_exam_attempts import ROOT, ROWS, seed_attempt_bank

BAD_ROW = 804   # trắc nghiệm không có phương án nào


def options(flags):
    return list(enumerate(flags, 1))


# mã câu → (loại, đáp án chuỗi, cờ đúng/sai của các phương án)
BANK = {
    1: ("SINGLE_CHOICE", None, [True, False, False, False]),
    2: ("SINGLE_CHOICE", None, [None, None, None, None]),       # chưa gắn đáp án
    3: ("SINGLE_CHOICE", None, [True, True, False, False]),     # hai đáp án đúng
    4: ("SINGLE_CHOICE", None, []),                             # không có phương án
    5: ("TRUE_FALSE", None, [True, False, True, False]),
    6: ("TRUE_FALSE", None, [True, None, True, False]),         # thiếu cờ một ý
    7: ("TRUE_FALSE", None, [True, False, True]),               # chỉ 3 ý
    8: ("SHORT_ANSWER", "12", []),
    9: ("SHORT_ANSWER", "   ", []),
    10: ("SHORT_ANSWER", None, []),
    11: ("ESSAY", "x", []),                                      # không chấm tự động được
}


async def seed_mixed(conn):
    await conn.execute(insert(chapters), {"chapter_id": 1, "code": "12C1", "name": "Đạo hàm", "parent_chapter_id": None, "level": 0})
    await conn.execute(insert(questions), [
        {"question_id": qid, "content": f"Câu {qid}", "type": kind, "difficulty": "TH", "grade": 12,
         "visibility": "PUBLISHED", "correct_answer": answer} for qid, (kind, answer, _) in BANK.items()])
    await conn.execute(insert(questions_chapters), [{"question_id": qid, "chapter_id": 1} for qid in BANK])
    await conn.execute(insert(statements), [
        {"statement_id": qid * 10 + number, "question_id": qid, "order": number, "content": f"Ý {number}", "is_correct": flag}
        for qid, (_, _, flags) in BANK.items() for number, flag in options(flags)])


@pytest.mark.asyncio
async def test_only_questions_with_a_usable_answer_key_are_picked():
    async with chat_client(seed_fn=seed_mixed) as client, client.db() as session:
        everything = QuestionBankRepository(session)
        strict = QuestionBankRepository(session, gradable_only=True)
        for kind, expected in [("SINGLE_CHOICE", [1]), ("TRUE_FALSE", [5]), ("SHORT_ANSWER", [8]), ("ESSAY", [])]:
            assert (await strict.pick_for_section(question_type=kind, n=20, chapter_codes=["12C1"])).question_ids == expected
        assert len((await everything.pick_for_section(question_type="SINGLE_CHOICE", n=20)).question_ids) == 4
        # Chương không chỉ định loại câu (luồng cũ) cũng chỉ lấy câu chấm được.
        assert sorted((await strict.pick("12C1", "TH", 20)).question_ids) == [1, 5, 8]


async def seed_with_bad_question(conn):
    await seed_attempt_bank(conn)
    await conn.execute(text("INSERT INTO questions (question_id, content, type, difficulty, visibility) "
                            "VALUES (:qid, 'Câu chưa có đáp án', 'SINGLE_CHOICE', 'NB', 'PUBLISHED')"), {"qid": BAD_ROW})


@pytest.mark.asyncio
async def test_old_draft_with_an_ungradable_question_still_starts_and_rescales_points():
    async with chat_client(real_auth=True, seed_fn=seed_with_bad_question) as client:
        owner = await login_as(client, "ungradable-owner@example.com")
        async with client.db() as session:
            chat = ExamChatSession(student_ref=f"U{owner}", user_id=owner)
            session.add(chat)
            await session.flush()
            loaded = await QuestionBankRepository(session).load_items([BAD_ROW, *[qid for qid, _ in ROWS]])
            draft = ExamDraft(
                session_id=chat.session_id, title="Đề cũ", preview_version=1,
                structure={"kind": "CHAPTER", "chapters": [{"code": "12C1", "count": 4}], "duration_minutes": None},
                items=[{"order": number, "chapter": "12C1", **item} for number, item in enumerate(loaded.values(), 1)],
                shortages=[])
            session.add(draft)
            await session.commit()
            draft_id = draft.draft_id
        started = await client.post(f"{ROOT}/exams/{draft_id}/attempts", json={})
        assert started.status_code == 200, started.text
        items = started.json()["draft"]["items"]
        assert sorted(item["code"] for item in items) == ["Q00801", "Q00802", "Q00803"]
        assert [item["order"] for item in items] == [1, 2, 3]
        assert round(sum(item["max_points"] for item in items), 6) == 10
        assert started.json()["total"] == 3
