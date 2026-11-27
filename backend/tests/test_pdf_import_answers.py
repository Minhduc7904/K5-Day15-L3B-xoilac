import pytest

from app.schemas.pdf_import import AnswerEvidence, ExtractedQuestion, Extraction
from app.usecase.pdf_import_answers import build_drafts


def question(section, kind, statements=None, number="1"):
    return ExtractedQuestion(
        section=section, number=number, pages=[1, 2], type=kind,
        content="Câu hỏi ![media:10](media:10)", statements=statements or [], image_dependent=True,
    )


def evidence(section, source, excerpt, **kwargs):
    return AnswerEvidence(
        section=section, number="1", page=3, source=source, excerpt=excerpt,
        choices=kwargs.get("choices"), truth_values=kwargs.get("truth_values"),
        answer=kwargs.get("answer"), solution=kwargs.get("solution"),
    )


PAGES = [
    {"page": 1, "normalized": "![media:10](media:10)"},
    {"page": 2, "normalized": "![media:11](media:11)"},
    {"page": 3, "normalized": "I 1 D\nII 1 Đ S\nIII 1 2,41\nGiải: 2.41\n![media:12](media:12)"},
]


def test_matches_sections_and_reconciles_all_question_types():
    data = Extraction(
        questions=[
            question("I", "SINGLE_CHOICE", ["a", "b", "c", "![media:11](media:11)"]),
            question("II", "TRUE_FALSE", ["a", "b"]),
            question("III", "SHORT_ANSWER"),
            question("IV", "MULTIPLE_CHOICE", ["a", "b", "c"]),
            question("V", "ESSAY"),
        ],
        answers=[
            evidence("I", "key", "I 1 D", choices=[4]),
            evidence("II", "key", "II 1 Đ S", truth_values=[True, False]),
            evidence("III", "key", "III 1 2,41", answer="2,41"),
            evidence("III", "solution", "Giải: 2.41", answer="$2.41$",
                     solution="Giải: 2.41 ![media:12](media:12)"),
            evidence("IV", "solution", "Giải: 2.41", choices=[3, 1]),
            evidence("V", "solution", "Giải: 2.41", solution="Giải: 2.41"),
        ],
    )
    one, tf, short, multiple, essay = build_drafts(data, PAGES)
    assert [item["isCorrect"] for item in one["statements"]] == [False, False, False, True]
    assert "media:11" in one["statements"][3]["content"]
    assert [item["isCorrect"] for item in tf["statements"]] == [True, False]
    assert short["answerState"] == "resolved" and short["correctAnswer"] == "2,41"
    assert len(short["evidence"]) == 2 and "media:12" in short["solution"]
    assert [item["isCorrect"] for item in multiple["statements"]] == [True, False, True]
    assert essay["correctAnswer"] is None and essay["solution"] == "Giải: 2.41"


@pytest.mark.parametrize(("answers", "state", "values"), [
    ([], "missing", [None, None]),
    ([evidence("II", "key", "II 1 Đ S", truth_values=[None, False])], "missing", [None, False]),
    ([evidence(None, "key", "II 1 Đ S", truth_values=[True, False])], "ambiguous", [None, None]),
    ([
        evidence("II", "key", "II 1 Đ S", truth_values=[True, False]),
        evidence("II", "solution", "Giải: 2.41", truth_values=[False, False]),
    ], "conflict", [None, None]),
    ([evidence("II", "key", "not in OCR", truth_values=[True, False])], "missing", [None, None]),
])
def test_flags_unresolved_answer_without_coercing_false(answers, state, values):
    cases = Extraction(questions=[question("I", "SHORT_ANSWER"), question("II", "TRUE_FALSE", ["a", "b"])],
                       answers=answers)
    result = build_drafts(cases, PAGES)[1]
    assert result["answerState"] == state
    assert [item["isCorrect"] for item in result["statements"]] == values
    assert f"answer_{state}" in result["flags"]
