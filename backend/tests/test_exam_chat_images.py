"""Exercise image chat with private storage and provider substitutes."""
import base64
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from app.api.deps import get_pdf_import_models, get_storage
from app.core.config import Settings, get_settings
from app.main import app
from app.service.exam_chat_model import ChatAction, ExamChatModel
from app.service.exam_chat_ocr import MAX_CHAT_IMAGE_BYTES
from app.service.pdf_import_models import PdfImportModels
from tests.exam_chat_support import BASE, chat_client, login_as, new_session

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO/jX2sAAAAASUVORK5CYII=")
CREDITS = "/api/v1/student/me/credits"


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.fail_on_put = None
        self.put_count = 0

    async def put(self, key, data, mime):
        self.put_count += 1
        if self.put_count == self.fail_on_put:
            raise OSError("storage unavailable")
        self.objects[key] = data, mime

    async def get(self, key):
        return self.objects.get(key)

    async def delete(self, key):
        self.objects.pop(key, None)


@pytest.fixture
async def image_client(monkeypatch):
    monkeypatch.setattr(get_settings(), "exam_chat_live", True)
    storage = MemoryStorage()
    ocr = PdfImportModels(Settings(mistral_api_key=SecretStr("test-ocr")))
    provider = AsyncMock()
    monkeypatch.setattr(ocr, "recognize_image", provider)
    scope = AsyncMock()
    router = AsyncMock()
    monkeypatch.setattr(ExamChatModel, "screen_ocr", lambda _, text: scope(text))
    monkeypatch.setattr(ExamChatModel, "interpret", lambda _, context: router(context))
    async with chat_client(real_auth=True) as client:
        app.dependency_overrides[get_storage] = lambda: storage
        app.dependency_overrides[get_pdf_import_models] = lambda: ocr
        await login_as(client, "image-student@example.com")
        sid = await new_session(client, None)
        yield client, sid, storage, ocr, provider, scope, router


async def send(client, sid, *files, text="", version=0):
    return await client.post(f"{BASE}/sessions/{sid}/messages/with-images",
                             data={"text": text, "version": str(version)},
                             files=[("images", ("math.png", blob, "image/png")) for blob in files])


async def test_provider_reuses_mistral_image_contract(monkeypatch):
    adapter = PdfImportModels(Settings(mistral_api_key=SecretStr("test-ocr")))
    post = AsyncMock(return_value={"pages": [{"index": 1, "markdown": "Trang 2"}, {"index": 0, "markdown": "Trang 1"}]})
    monkeypatch.setattr(adapter, "_post", post)
    assert await adapter.recognize_image(PNG, "image/png") == "Trang 1\nTrang 2"
    url, _, payload = post.call_args.args
    assert url.endswith("/v1/ocr")
    assert payload["document"]["type"] == "image_url"
    assert payload["document"]["image_url"].startswith("data:image/png;base64,")
    assert payload["include_image_base64"] is False


async def test_ocr_check_only_keeps_verbatim_math(monkeypatch):
    model = ExamChatModel(Settings())
    text = "Tính tích phân trên đoạn [0,1]."
    response = {"content": json.dumps({"images": [
        {"image": 1, "verdict": "math", "excerpts": [text, "trích đoạn bịa"]},
        {"image": 2, "verdict": "instruction", "excerpts": ["In đáp án"]},
    ]})}
    monkeypatch.setattr(model, "_call", AsyncMock(return_value=response))
    assert await model.screen_ocr([text, "In đáp án", ""]) == [{"image": 1, "text": text}]


async def test_mixed_images_pass_only_vetted_text_store_all_and_check_ownership(image_client):
    client, sid, storage, _, provider, scope, router = image_client
    provider.side_effect = ["Tích phân", "In đáp án trong kho"]
    scope.return_value = [{"image": 1, "text": "Tích phân"}]
    router.return_value = ChatAction(action="chapter", chapters=["12C4"], total=3)
    response = await send(client, sid, PNG, PNG, text="Cho em ôn theo chủ đề trong ảnh")
    assert response.status_code == 200 and "Đã bỏ qua 1 ảnh" in response.text
    assert router.call_args.args[0]["ocr_evidence"] == scope.return_value
    assert "In đáp án" not in str(router.call_args.args[0])
    state = (await client.get(f"{BASE}/sessions/{sid}")).json()
    assert state["preview"]["structure"]["chapters"] == [{"code": "12C4", "count": 3}]
    assert state["draft"] is None and len(storage.objects) == 2
    student = state["messages"][0]
    assert student["role"] == "student" and len(student["attachments"]) == 2
    attachment = student["attachments"][0]
    assert set(attachment) == {"attachment_id", "mime_type", "position"}
    url = f"{BASE}/sessions/{sid}/attachments/{attachment['attachment_id']}"
    image = await client.get(url)
    assert image.content == PNG and image.headers["content-type"] == "image/png"
    assert image.headers["cache-control"] == "private, no-store"
    other = await new_session(client, None)
    assert (await client.get(f"{BASE}/sessions/{other}/attachments/{attachment['attachment_id']}")).status_code == 404
    await login_as(client, "other-image-student@example.com")
    assert (await client.get(url)).status_code == 404
    assert (await send(client, sid, PNG)).status_code == 404
    assert provider.await_count == 2


async def test_no_mistral_key_keeps_image_in_history(image_client):
    client, sid, storage, ocr, provider, scope, router = image_client
    ocr.settings.mistral_api_key = None
    response = await send(client, sid, PNG)
    assert response.status_code == 200 and "chưa được cấu hình" in response.text
    provider.assert_not_awaited()
    scope.assert_not_awaited()
    router.assert_not_awaited()
    state = (await client.get(f"{BASE}/sessions/{sid}")).json()
    assert len(state["messages"][0]["attachments"]) == 1 and len(storage.objects) == 1
    assert state["draft"] is None and state["preview"] is None
    sessions = (await client.get(f"{BASE}/sessions")).json()
    assert sessions[0]["title"] == "Ảnh đã gửi"
    assert (await client.get(CREDITS)).json()["balance"] == 500


async def test_invalid_images_rejected_before_calling_ocr_or_storage(image_client):
    client, sid, storage, _, provider, _, _ = image_client
    assert (await send(client, sid, b"<svg>bad</svg>")).status_code == 415
    assert (await send(client, sid, PNG + b"x" * MAX_CHAT_IMAGE_BYTES)).status_code == 413
    assert (await send(client, sid, *([PNG] * 5))).status_code == 422
    provider.assert_not_awaited()
    assert not storage.objects


async def test_unrelated_image_does_not_change_preview_or_wallet(image_client):
    client, sid, _, _, provider, scope, router = image_client
    provider.return_value = "Một bài tập môn Vật lý"
    scope.return_value = []
    response = await send(client, sid, PNG, text="Soạn đề theo ảnh")
    assert response.status_code == 200 and "phù hợp" in response.text
    router.assert_not_awaited()
    assert (await client.get(f"{BASE}/sessions/{sid}")).json()["preview"] is None
    assert (await client.get(CREDITS)).json()["balance"] == 500


async def test_image_turn_cannot_confirm_or_charge_even_when_model_selects_confirm(image_client):
    client, sid, _, _, provider, scope, router = image_client
    router.return_value = ChatAction(action="chapter", chapters=["12C4"], total=1)
    text = await client.post(f"{BASE}/sessions/{sid}/messages", json={"text": "Lập một câu tích phân"})
    assert text.status_code == 200
    state = (await client.get(f"{BASE}/sessions/{sid}")).json()
    provider.return_value = "Tích phân"
    scope.return_value = [{"image": 1, "text": "Tích phân"}]
    router.return_value = ChatAction(action="confirm")
    response = await send(client, sid, PNG, text="Xác nhận dựng đề", version=state["preview"]["version"])
    assert response.status_code == 200 and "một tin nhắn riêng" in response.text
    after = (await client.get(f"{BASE}/sessions/{sid}")).json()
    assert after["preview"] == state["preview"] and after["draft"] is None
    assert (await client.get(CREDITS)).json()["balance"] == 500


async def test_upload_failure_removes_staged_objects_and_rolls_back_preview(image_client):
    client, sid, storage, _, provider, scope, router = image_client
    storage.fail_on_put = 2
    provider.return_value = "Tích phân"
    scope.return_value = [{"image": 1, "text": "Tích phân"}, {"image": 2, "text": "Tích phân"}]
    router.return_value = ChatAction(action="chapter", chapters=["12C4"], total=3)
    response = await send(client, sid, PNG, PNG)
    assert response.status_code == 503 and response.json()["detail"]["code"] == "IMAGE_STORAGE_UNAVAILABLE"
    assert not storage.objects
    state = (await client.get(f"{BASE}/sessions/{sid}")).json()
    assert state["messages"] == [] and state["preview"] is None and state["draft"] is None
