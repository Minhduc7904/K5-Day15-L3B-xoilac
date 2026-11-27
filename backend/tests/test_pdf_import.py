import base64
import json
import re
from io import BytesIO
from pathlib import Path
from runpy import run_path

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_pdf_import_models, get_storage
from app.core.config import get_settings
from app.core.database import get_session, get_sessionmaker
from app.main import app
from app.models import Base, PdfReferenceVector
from app.repositories.pdf_imports import PdfImportRepository, question_chapters, questions
from app.service.pdf_import_models import PdfImportModels
from app.usecase.pdf_import_classification import classify_drafts
from tests.conftest import FakeStorage
from tests.test_auth import login, make_admin, register

ROOT = "/api/v1/admin/pdf-imports"
FIGURE = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XufkAAAAASUVORK5CYII="
)


def fixture_pdf(*, scanned: bool) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    stream = DecodedStreamObject()
    if scanned:
        image = DecodedStreamObject()
        image.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(32),
            NameObject("/Height"): NumberObject(32),
            NameObject("/ColorSpace"): NameObject("/DeviceGray"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        })
        image.set_data(bytes(0 if x == y or x == 16 or y == 16 else 255 for y in range(32) for x in range(32)))
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/XObject"): DictionaryObject({NameObject("/Figure"): writer._add_object(image)})
        })
        stream.set_data(b"q 160 0 0 160 20 20 cm /Figure Do Q")
    else:
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): DictionaryObject({
                NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })})
        })
        stream.set_data(b"BT /F1 12 Tf 25 170 Td (Cau 1. Chon do thi. Dap an D.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class FixtureModels(PdfImportModels):
    embedding_calls = 0

    async def _post(self, url, key, body, timeout):
        if url.endswith("/ocr"):
            assert body["include_image_base64"] is True
            encoded = body["document"]["document_url"].split(",", 1)[1]
            assert len(PdfReader(BytesIO(base64.b64decode(encoded))).pages) == 1
            return {"model": "fixture-ocr", "pages": [{
                "index": 0,
                "markdown": "I. Câu 1. Chọn đồ thị $y=x$. A. text B. text C. text D. ![img](img.png)\nI. 1 D",
                "images": [{"id": "img.png", "image_base64": f"data:image/png;base64,{FIGURE}"}],
            }]}
        if url.endswith("/embeddings"):
            self.embedding_calls += 1
            return {"data": [
                {"index": i, "embedding": [0.0, 1.0] if "không liên quan" in value else [1.0, 0.0]}
                for i, value in enumerate(body["input"])
            ]}
        assert url.endswith("/chat/completions")
        assert body["response_format"]["json_schema"]["strict"] is True
        media = re.search(r"!\[media:\d+\]\(media:\d+\)", body["messages"][1]["content"]).group()
        data = {
            "questions": [{
                "section": "I", "number": "1", "pages": [1], "type": "SINGLE_CHOICE",
                "content": "Chọn đồ thị $y=x$.", "statements": ["A", "B", "C", media],
                "image_dependent": True,
            }],
            "answers": [{
                "section": "I", "number": "1", "page": 1, "source": "key", "excerpt": "I. 1 D",
                "choices": [4], "truth_values": None, "answer": None, "solution": None,
            }],
        }
        return {"model": "fixture-extraction", "choices": [{
            "finish_reason": "stop", "message": {"content": json.dumps(data)},
        }]}


@pytest.fixture
async def pdf_api(tmp_path, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    get_settings.cache_clear()
    storage = FakeStorage()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'imports.db'}")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    ddl = run_path(str(Path(__file__).resolve().parents[1] / "alembic/versions/0002_base_content.py"))["STATEMENTS"]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for statement in ddl:
            await conn.exec_driver_sql(
                statement.replace("integer GENERATED BY DEFAULT AS IDENTITY", "integer")
                .replace("DEFAULT now()", "DEFAULT CURRENT_TIMESTAMP")
            )
        await conn.exec_driver_sql("INSERT INTO subjects (subject_id, name, code) VALUES (1, 'Toán', 'MATH')")
        await conn.exec_driver_sql(
            "INSERT INTO chapters (chapter_id, subject_id, code, name, slug, order_in_parent)"
            " VALUES (1, 1, '12C1', 'Đạo hàm', 'dao-ham', 1)"
        )

    async def session_override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_sessionmaker] = lambda: maker
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_pdf_import_models] = lambda: FixtureModels(get_settings())
    try:
        await make_admin(maker)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, maker, storage
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        await engine.dispose()


@pytest.mark.parametrize("scanned", [True, False])
async def test_upload_preview_approve_and_read(pdf_api, scanned):
    client, sessions, storage = pdf_api
    data = fixture_pdf(scanned=scanned)
    assert bool(PdfReader(BytesIO(data)).pages[0].extract_text()) is not scanned
    assert (await client.get(ROOT)).status_code == 401
    assert (await register(client)).status_code == 201
    assert (await client.get(ROOT)).status_code == 403
    assert (await login(client, email="admin@example.com")).status_code == 200
    upload = await client.post(ROOT, files={"file": ("exam.pdf", data, "application/pdf")})
    assert upload.status_code == 202, upload.text
    assert upload.json()["status"] == "queued"
    path = upload.json()["statusUrl"]
    imported = (await client.get(path)).json()
    assert imported["status"] == "ready_for_review", imported
    assert imported["draftCount"] == 1
    draft, = (await client.get(f"{path}/drafts")).json()
    assert [option["isCorrect"] for option in draft["statements"]] == [False, False, False, True]
    assert draft["sourcePages"] == [1]
    media_id = re.search(r"media:(\d+)", draft["statements"][3]["content"])[1]
    signed = (await client.get(f"{path}/media/{media_id}/url")).json()["url"]
    image = await client.get(signed)
    assert image.content == base64.b64decode(FIGURE)
    assert image.headers["content-type"] == "image/png"
    assert (await client.get(signed + "wrong")).status_code == 403
    async with sessions() as db:
        assert (await db.execute(select(questions))).all() == []

    review = f"{path}/drafts/{draft['id']}"
    assert (await client.post(f"{review}/approve")).status_code == 422
    saved = await client.patch(review, json={
        "chapterCodes": ["12C1"], "difficulty": "TH", "imageReviewed": True,
    })
    assert saved.status_code == 200, saved.text
    # READY metadata is insufficient if the underlying crop is missing.
    image_key = next(key for key in storage.objects if key.endswith(".png"))
    image_data = storage.objects.pop(image_key)
    assert (await client.post(f"{review}/approve")).status_code == 422
    storage.objects[image_key] = image_data
    approved = await client.post(f"{review}/approve")
    assert approved.status_code == 200, approved.text
    question_id = approved.json()["questionId"]
    assert (await client.post(f"{review}/approve")).json()["questionId"] == question_id
    async with sessions() as db:
        question = await PdfImportRepository(db).read_published_question(question_id)
    assert question["content"] == "Chọn đồ thị $y=x$."
    assert list(question["statements"][3]) == ["content", "order"]
    assert question["chapterCodes"] == ["12C1"]
    assert "correct_answer" not in question and "solution" not in question


async def test_invalid_pdf_and_rejected_draft_do_not_publish(pdf_api):
    client, sessions, _ = pdf_api
    assert (await login(client, email="admin@example.com")).status_code == 200
    assert (await client.post(ROOT, files={"file": ("bad.pdf", b"invalid")})).status_code == 415
    assert (await client.post(ROOT, files={"file": ("bad.pdf", b"%PDF-broken")})).status_code == 422
    upload = await client.post(ROOT, files={"file": ("exam.pdf", fixture_pdf(scanned=False))})
    path = upload.json()["statusUrl"]
    draft, = (await client.get(f"{path}/drafts")).json()
    review = f"{path}/drafts/{draft['id']}"
    assert (await client.post(f"{review}/reject")).json()["status"] == "rejected"
    assert (await client.post(f"{review}/approve")).status_code == 409
    async with sessions() as db:
        assert (await db.execute(select(questions))).all() == []


async def test_reference_cache_uses_published_questions_and_abstains(pdf_api):
    _, sessions, _ = pdf_api
    models = FixtureModels(get_settings())
    async with sessions() as session:
        ids = []
        for visibility in ["PUBLISHED", "DRAFT", "PRIVATE"]:
            row = await session.execute(insert(questions).values(
                content=f"Tính đạo hàm $x^2$ {visibility}.", slug=visibility.lower(), type="SHORT_ANSWER",
                difficulty="TH", grade=12, subject_id=1, visibility=visibility,
            ).returning(questions.c.question_id))
            question_id = row.scalar_one()
            ids.append(question_id)
            await session.execute(insert(question_chapters).values(question_id=question_id, chapter_id=1))
        await session.commit()
        repo = PdfImportRepository(session)
        matched, weak = (
            {"content": content, "imageDependent": False, "statements": [], "flags": []}
            for content in ["Đạo hàm của $x^3$.", "Câu không liên quan."]
        )
        await classify_drafts([matched, weak], repo, models)
        await session.commit()
        labels = matched["suggestions"]
        assert (labels["chapter"], labels["grade"], labels["difficulty"]) == ("12C1", 12, "TH")
        assert [n["questionId"] for n in labels["neighbors"]] == ids[:1]
        assert labels["neighbors"][0]["similarity"] == 1
        assert weak["suggestions"]["chapter"] is None and weak["flags"] == ["label_review"]
        assert list(await session.scalars(select(PdfReferenceVector.question_id))) == ids[:1]
        calls = models.embedding_calls
        await classify_drafts([matched], repo, models)
        assert models.embedding_calls == calls + 1   # Query only, cached reference reused.
        await session.execute(update(questions).where(questions.c.question_id == ids[0]).values(visibility="PRIVATE"))
        await session.commit()
        await classify_drafts([matched], repo, models)
        assert matched["suggestions"]["neighbors"] == []


async def test_ocr_adapter_output_contract(monkeypatch):
    from app.core.config import Settings
    from app.service.pdf_import_models import OcrImage, OcrPage

    async def post(url, key, body, timeout):
        assert url.endswith("/ocr")
        assert body["model"] == "selected-mistral"
        return {"pages": [
            {"index": 1, "markdown": "Trang 2", "images": [{"id": "bad.png", "image_base64": "?"}]},
            {"index": 0, "markdown": "Trang 1", "images": [{"id": "figure.png", "image_base64": FIGURE}]},
        ]}

    settings = Settings(ocr_provider="mistral", ocr_model="selected-mistral", mistral_api_key="fixture")
    models = PdfImportModels(settings)
    monkeypatch.setattr(models, "_post", post)
    model, pages = await models.recognize(b"test")
    assert model == "selected-mistral"
    assert pages == [
        OcrPage(0, "Trang 1", [OcrImage("figure.png", base64.b64decode(FIGURE))]),
        OcrPage(1, "Trang 2", [OcrImage("bad.png", None)]),
    ]


async def test_extraction_retries_truncated_output_with_page_ownership(monkeypatch):
    from app.core.config import Settings

    pages = [{"page": page, "normalized": f"Phần I\nTrang {page}"} for page in range(1, 7)]
    requests = []

    async def post(url, key, body, timeout):
        instructions = body["messages"][0]["content"]
        requests.append(instructions)
        if len(requests) == 1:
            return {"choices": [{"finish_reason": "length", "message": {"content": ""}}]}
        questions = [{
            "section": "I", "number": str(page), "pages": [page], "type": "SHORT_ANSWER",
            "content": f"Câu {page}", "statements": [], "image_dependent": False,
        } for page in ([1, 4, 5] if len(requests) == 2 else [4, 5, 6])]
        return {"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps({"questions": questions, "answers": []})},
        }]}

    models = PdfImportModels(Settings(openai_api_key="fixture"))
    monkeypatch.setattr(models, "_post", post)
    _, result = await models.extract(pages)
    assert [question.number for question in result.questions] == ["1", "4", "5", "6"]
    assert "pages [1, 2, 3, 4]" in requests[1]
    assert "pages [5, 6]" in requests[2]


async def test_ocr_failure_leaves_a_failed_session_without_drafts(pdf_api, monkeypatch):
    client, _, _ = pdf_api

    async def fail_recognition(self, pdf):
        raise ValueError("fixture internal provider payload")

    monkeypatch.setattr(FixtureModels, "recognize", fail_recognition)
    assert (await login(client, email="admin@example.com")).status_code == 200
    response = await client.post(ROOT, files={"file": ("scan.pdf", fixture_pdf(scanned=True))})
    assert response.status_code == 202
    status = (await client.get(response.json()["statusUrl"])).json()
    assert status["status"] == "failed" and status["stage"] == "ocr"
    assert status["draftCount"] == 0 and "fixture internal" not in status["error"]
