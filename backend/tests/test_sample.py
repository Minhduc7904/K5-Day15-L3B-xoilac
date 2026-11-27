async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": True, "storage": True}


async def test_sample_item_roundtrip(client):
    created = await client.post("/api/v1/sample-items", json={"name": "  đề mẫu  "})
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "đề mẫu"

    got = await client.get(f"/api/v1/sample-items/{body['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]

    listed = await client.get("/api/v1/sample-items")
    assert [i["id"] for i in listed.json()] == [body["id"]]


async def test_sample_item_validation_and_404(client):
    assert (await client.post("/api/v1/sample-items", json={"name": ""})).status_code == 422
    assert (await client.get("/api/v1/sample-items/999")).status_code == 404


async def test_sample_file_roundtrip(client):
    payload = "Xin chào MinIO".encode()
    up = await client.post("/api/v1/sample-files", files={"file": ("a.txt", payload, "text/plain")})
    assert up.status_code == 201
    key = up.json()["key"]
    assert up.json()["size"] == len(payload)

    down = await client.get(f"/api/v1/sample-files/{key}")
    assert down.status_code == 200
    assert down.content == payload
    assert down.headers["content-type"].startswith("text/plain")


async def test_sample_file_rejects_foreign_key_and_missing(client):
    assert (await client.get("/api/v1/sample-files/other/secret")).status_code == 404
    assert (await client.get("/api/v1/sample-files/samples/none")).status_code == 404
