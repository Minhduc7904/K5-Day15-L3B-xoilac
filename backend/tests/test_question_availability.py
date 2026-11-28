"""#11: câu đã lưu trữ (questions.archived_at) không bao giờ được pipeline #4 chọn cho đề mới.

Kiểm cả ba đường chọn câu của #4 (pick, pick_for_section, practice_capacity) và điều kiện dùng chung
available_questions(). Đọc lại câu đã nằm trong đề (load_items) vẫn được, để đề và lịch sử cũ không vỡ.
Dữ liệu là ngân hàng tự dựng ở tests/exam_chat_support.py.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.repositories.question_bank_repository import (
    QuestionBankRepository, available_questions, content_metadata, questions,
)
from tests.exam_chat_support import seed

ARCHIVED = [1, 2, 5, 40, 50]


@pytest.fixture
async def maker():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(content_metadata.create_all)
        await seed(conn)
        await conn.execute(update(questions).where(questions.c.question_id.in_(ARCHIVED))
                           .values(archived_at=datetime.now(timezone.utc)))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_predicate_excludes_archived_and_unpublished(maker):
    async with maker() as s:
        ids = set((await s.execute(select(questions.c.question_id).where(available_questions()))).scalars())
    assert ids and not ids & set(ARCHIVED)
    assert 11 not in ids and 43 not in ids          # DRAFT
    assert 3 in ids                                 # PUBLISHED, chưa lưu trữ


async def test_pipeline_selection_never_picks_archived(maker):
    async with maker() as s:
        bank = QuestionBankRepository(s)
        picked = await bank.pick("12C1", "TH", 50)
        assert picked.question_ids == [3, 4, 41, 42]      # pick không lọc loại câu; 1, 2, 40 đã lưu trữ
        assert picked.available == 4

        tf = await bank.pick_for_section(question_type="TRUE_FALSE", n=10, chapter_codes=["12C1"])
        assert tf.question_ids == [41, 42]

        short = await bank.pick_for_section(question_type="SHORT_ANSWER", n=10, chapter_codes=["12C4"])
        assert short.question_ids == [] and short.available == 0

        cells, total = await bank.practice_capacity(["12C1"], ["TH", "VD"], ["SINGLE_CHOICE"])
        by_cell = {(c["difficulty"], c["type"]): c["available"] for c in cells}
        assert by_cell[("TH", "SINGLE_CHOICE")] == 2 and by_cell[("VD", "SINGLE_CHOICE")] == 2
        assert total == 4


async def test_archived_question_still_readable_in_existing_exam(maker):
    async with maker() as s:
        items = await QuestionBankRepository(s).load_items([1, 3])
    assert set(items) == {1, 3}
