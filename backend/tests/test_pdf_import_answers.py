from types import SimpleNamespace

import pytest

from app.schemas.pdf_import import AnswerEvidence, ExtractedQuestion, Extraction
from app.usecase.pdf_import_answers import build_drafts
from app.usecase.pdf_import_question_source import reconcile_vector_choices


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


def test_restores_stem_fragments_and_explicit_choice_order():
    data = Extraction(
        questions=[
            question("I", "SINGLE_CHOICE", ["![media:11](media:11)", "Choose:",
                                             "A. one", "B. two", "C. three", "D. four"]),
            question("III", "SHORT_ANSWER", ["![media:11](media:11)", "Find the result."]),
        ],
        answers=[evidence("I", "key", "I 1 D", choices=[4])],
    )
    choice, short = build_drafts(data, PAGES)
    assert "media:11" in choice["content"] and "Choose:" in choice["content"]
    assert [option["content"] for option in choice["statements"]] == ["one", "two", "three", "four"]
    assert [option["isCorrect"] for option in choice["statements"]] == [False, False, False, True]
    assert short["statements"] == [] and "media:11" in short["content"]


def test_matches_unlabeled_choices_to_the_complete_source_option_block():
    draft = question("I", "SINGLE_CHOICE", ["Choose:", "one", "two", "three", "four"])
    answers = [evidence("I", "key", "I 1 D", choices=[4])]
    pages = [*PAGES]
    pages[0] = {"page": 1, "normalized": "![media:10](media:10)\nA. one B. two C. three D. four"}
    result, = build_drafts(Extraction(questions=[draft], answers=answers), pages)
    assert [option["content"] for option in result["statements"]] == ["one", "two", "three", "four"]
    assert "Choose:" in result["content"]


def test_copies_worked_solutions_by_section_and_keeps_continuation_page():
    pages = [
        {"page": 1, "normalized": "PHẦN I.\nCâu 1. Dòng nằm trong đề\n![media:10](media:10)"},
        {"page": 2, "normalized": "PHẦN II.\nCâu 1. Câu hỏi khác"},
        {"page": 3, "normalized": "# **ĐÁP ÁN VÀ LỜI GIẢI THAM KHẢO**\n"
         "# PHẦN I.\n| Câu | Đáp án |\n| 1 | B |\n"
         "# PHẦN I.\n## Câu 1. Chọn A.\nGiữ $x^2$."},
        {"page": 4, "normalized": "Tiếp theo **chọn A**.\n![media:13](media:13)\n"
         "# **PHẦN II.**\n**Câu 1.** Đáp số: 4\nGiải riêng của phần II.\n--- HẾT ---\nGhi chú"},
    ]
    answers = [
        evidence("I", "key", "| 1 | B |", choices=[2]),
        evidence("I", "solution", "Tiếp theo chọn A.", choices=[1], solution="Không dùng lại văn bản model."),
        evidence("II", "solution", "Giải riêng của phần II.", answer="4", solution="Không dùng lại văn bản model."),
    ]
    one, two = build_drafts(Extraction(
        questions=[question("I", "SINGLE_CHOICE", ["one", "two"]), question("II", "SHORT_ANSWER")],
        answers=answers,
    ), pages)
    assert one["solution"] == ("## Câu 1. Chọn A.\nGiữ $x^2$.\n\n"
                               "Tiếp theo **chọn A**.\n![media:13](media:13)")
    assert one["solutionPages"] == [3, 4]
    assert "image_source_mismatch" not in one["flags"]
    assert one["answerState"] == "conflict"
    assert one["evidence"][1]["page"] == 4
    assert two["solution"] == "**Câu 1.** Đáp số: 4\nGiải riêng của phần II."
    assert two["solutionPages"] == [4] and two["correctAnswer"] == "4"


def test_duplicate_worked_solution_numbers_are_flagged_without_guessing():
    pages = [
        *PAGES,
        {"page": 4, "normalized": "# LỜI GIẢI CHI TIẾT\n# PHẦN I.\nCâu 1.\nGiải thứ nhất.\n"
         "Câu 1.\nGiải thứ hai."},
    ]
    candidate = evidence("I", "solution", "Giải thứ nhất.", answer="10", solution="Giải thứ nhất.")
    candidate = candidate.model_copy(update={"page": 4})
    draft, = build_drafts(Extraction(questions=[question("I", "SHORT_ANSWER")], answers=[candidate]), pages)
    assert draft["solution"] is None and draft["solutionPages"] == []
    assert draft["correctAnswer"] is None and "solution_review" in draft["flags"]


def test_solution_evidence_from_the_question_page_stays_unresolved():
    pages = [
        {"page": 1, "normalized": "PHẦN I.\nCâu 1. Dòng trong đề."},
        {"page": 2, "normalized": "# LỜI GIẢI\n# PHẦN I.\nCâu 1.\nDòng trong lời giải."},
    ]
    candidate = evidence("I", "solution", "Dòng trong đề.", answer="4", solution="Đoán")
    candidate = candidate.model_copy(update={"page": 1})
    draft, = build_drafts(Extraction(questions=[question("I", "SHORT_ANSWER")], answers=[candidate]), pages)
    assert draft["solution"] == "Câu 1.\nDòng trong lời giải."
    assert draft["correctAnswer"] is None and draft["answerState"] == "missing"


def test_solution_without_an_explicit_section_is_flagged():
    pages = [*PAGES, {"page": 4, "normalized": "# LỜI GIẢI\nCâu 1.\nGiải đây."}]
    data = Extraction(questions=[question("I", "SHORT_ANSWER"), question("II", "SHORT_ANSWER")], answers=[])
    assert all("solution_review" in draft["flags"] and draft["solution"] is None
               for draft in build_drafts(data, pages))


def test_restores_omitted_question_images_and_reads_explicit_worked_answers():
    crop = "![media:80](media:80)"
    option_crop = "![media:81](media:81)"
    pages = [
        {"page": 1, "normalized": f"PHẦN I.\n**Câu 1:** Có một vật thể.\n{crop}\n"
         f"Chọn hình tương ứng.\nA. Hình tròn B. {option_crop} C. Hình vuông D. Hình thoi\n"
         "Câu 2. Một câu khác.\nA. 1 B. 2 C. 3 D. 4\nLOGO\nTrang 1\n"},
        {"page": 2, "normalized": "PHẦN II.\nCâu 1. Xét bốn mệnh đề.\n"
         "a) Một.\nb) Hai.\nc) Ba.\nd) Bốn.\nPHẦN III.\nCâu 1. Tìm độ dài.\n"
         "LOGO\nTrang 2\n"},
        {"page": 3, "normalized": "# ĐÁP ÁN VÀ LỜI GIẢI THAM KHẢO\n"
         "PHẦN I.\n**Câu 1.** Hai hình giống nhau. Chọn B.\nCâu 2. Chọn C.\n"
         "PHẦN II.\n**Câu 1.**\na) Đúng.\nb) Sai.\nc) Đúng.\nd) Sai.\n"
         "PHẦN III.\n**Câu 1.** Có kết quả đã làm tròn. Đáp số: 13,9.\n--- HẾT ---"},
    ]
    questions = [
        question("I", "SINGLE_CHOICE", ["a", "b", "c", "d", "$"]),
        question("I", "SINGLE_CHOICE", ["1", "2", "3", "4"], number="2"),
        question("II", "TRUE_FALSE", ["Một.", "Hai.", "Ba.", "Bốn."]),
        question("III", "SHORT_ANSWER"),
    ]
    questions = [item.model_copy(update={"content": "Bản model thiếu dữ kiện", "image_dependent": False})
                 for item in questions]
    choice, other, true_false, short = build_drafts(Extraction(questions=questions, answers=[]), pages)
    assert choice["content"] == f"Có một vật thể.\n{crop}\nChọn hình tương ứng."
    assert choice["sourcePages"] == [1] and choice["solutionPages"] == [3]
    assert [option["content"] for option in choice["statements"]] == [
        "Hình tròn", option_crop, "Hình vuông", "Hình thoi",
    ]
    assert [option["isCorrect"] for option in choice["statements"]] == [False, True, False, False]
    assert choice["imageDependent"] and choice["flags"] == ["image_review"]
    assert "media:" not in other["content"] and other["answerState"] == "resolved"
    assert [option["isCorrect"] for option in true_false["statements"]] == [True, False, True, False]
    assert short["answerState"] == "resolved" and short["correctAnswer"] == "13,9"
    assert short["evidence"][0]["excerpt"] == "Đáp số: 13,9"


@pytest.mark.parametrize(("second_vector", "third_vector"), [("A′B′", "CC"), ("A′ B′", "CC"), ("A′B′", "CD")])
def test_verifies_vector_prime_marks_against_pdf_text_without_changing_the_answer(
    monkeypatch, second_vector, third_vector,
):
    source = (
        f"Câu 1: Khẳng định nào sai?\nA.−→AA′=−→BB′.B.−→{second_vector}=−→AB."
        f"C.−→{third_vector}′=−→DD′.D.−→BA′=−→BC′."
    )
    reader = SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: source)])
    monkeypatch.setattr("app.usecase.pdf_import_question_source.PdfReader", lambda _: reader)
    options = [
        r"$\overrightarrow{AA'} = \overrightarrow{BB'}$.",
        r"$\overrightarrow{A'B'} = \overrightarrow{AB'}$.",
        r"$\overrightarrow{CC'} = \overrightarrow{DD'}$.",
        r"$\overrightarrow{BA'} = \overrightarrow{BC'}$.",
    ]
    draft = {"type": "SINGLE_CHOICE", "number": "1", "sourcePages": [1],
             "statements": [{"content": value, "isCorrect": i == 3} for i, value in enumerate(options)]}
    reconcile_vector_choices(b"%PDF", [draft])
    expected = r"$\overrightarrow{A'B'} = \overrightarrow{AB}$." if third_vector == "CC" else options[1]
    assert draft["statements"][1]["content"] == expected
    assert [option["isCorrect"] for option in draft["statements"]] == [False, False, False, True]


@pytest.mark.parametrize("repeated", [False, True])
def test_reanchors_key_row_only_if_one_page_matches(repeated):
    key = evidence("III", "key", "|1|2,41|", answer="2,41").model_copy(update={"page": 12})
    pages = [*PAGES, {"page": 8, "normalized": "| 1 | 2,41 |"}]
    if repeated:
        pages.append({"page": 10, "normalized": "| 1 | 2,41 |"})
    case = Extraction(questions=[question("III", "SHORT_ANSWER")], answers=[key])
    draft, = build_drafts(case, pages)
    if repeated:
        assert draft["answerState"] == "missing"
        assert draft["evidence"] == []
    else:
        assert draft["correctAnswer"] == "2,41"
        assert draft["evidence"][0]["page"] == 8
