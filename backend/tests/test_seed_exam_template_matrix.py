"""Kiểm dữ liệu migration 0019 (mẫu cấu trúc đề Toán): hợp lệ theo luật của #5, mã chương có thật, không trùng khoá."""
import csv
import importlib.util
from pathlib import Path

import pytest

from app.schemas.exam_template import ExamTemplateIn
from app.usecase.exam_template_rules import check_template

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend" / "alembic" / "versions" / "0019_seed_exam_template_matrix.py"


def _load():
    spec = importlib.util.spec_from_file_location("seed_matrix_0019", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()
TEMPLATES = MOD.templates()


def _chapter_codes() -> set[str]:
    with open(ROOT / "data" / "chapters.csv", encoding="utf-8", newline="") as f:
        return {row["ma_chuong"] for row in csv.DictReader(f)}


def test_migration_chain():
    assert MOD.down_revision == "0018_chat_session_title"


def test_template_set_is_complete_and_unique():
    keys = [(t["name"], t["exam_type"], t["version_label"]) for t in TEMPLATES]
    assert len(keys) == len(set(keys)) == 14
    thpt = {t["version_label"] for t in TEMPLATES if t["exam_type"] == "THPT"}
    assert thpt == {"2025", "2026"}
    for grade in (10, 11, 12):
        kinds = {t["exam_type"] for t in TEMPLATES if t["grade"] == grade and t["exam_type"] != "THPT"}
        assert kinds == {"GK1", "CK1", "GK2", "CK2"}


@pytest.mark.parametrize("t", TEMPLATES, ids=lambda t: t["name"])
def test_template_passes_business_rules_for_approval(t):
    data = ExamTemplateIn(**{k: t[k] for k in ("name", "exam_type", "grade", "version_label", "duration_minutes", "source", "description", "sections")})
    assert check_template(data, for_approval=True) == []
    assert t["total_questions"] == sum(s["count"] for s in t["sections"])


def test_chapter_codes_exist_in_chapters_csv():
    known = _chapter_codes()
    used = {c for t in TEMPLATES for s in t["sections"] for c in s.get("chapter_codes", [])}
    assert used <= known, sorted(used - known)


def test_thpt_structure_is_12_4_6():
    for t in TEMPLATES:
        if t["exam_type"] == "THPT":
            assert [s["count"] for s in t["sections"]] == [12, 4, 6]
            assert t["total_questions"] == 22 and t["duration_minutes"] == 90
            assert t["status"] == "APPROVED"


def test_semester_templates_are_draft_and_points_sum_to_ten_where_known():
    for t in TEMPLATES:
        if t["exam_type"] == "THPT":
            continue
        assert t["status"] == "DRAFT"
        if t["grade"] == 12:
            total = sum(s["count"] * s["points_per_question"] for s in t["sections"])
            assert total == pytest.approx(10.0)
        elif t["grade"] == 11 and t["exam_type"] == "GK1":
            # 12 x 0,25 + 3 x 1 + 4 x 0,5 = 8; phần tự luận 2 đ nằm ngoài points_per_question.
            fixed = sum(s["count"] * s["points_per_question"] for s in t["sections"] if "points_per_question" in s)
            assert fixed == pytest.approx(8.0)
