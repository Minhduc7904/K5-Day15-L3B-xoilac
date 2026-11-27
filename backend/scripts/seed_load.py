"""Nạp gói dữ liệu nền vào PostgreSQL. Chạy trong container db-init, SAU `alembic upgrade head`.

- Không có `$SEED_DIR/content/manifest.json` → bỏ qua (chỉ có bảng, không có dữ liệu base).
- Đã có dấu `base_seed` trong `app_init_state` → bỏ qua. Nhờ vậy init chỉ nạp đúng một lần.
- Nạp trong MỘT giao dịch: lỗi thì không để lại dữ liệu nửa chừng và không đặt dấu.
Gói dữ liệu do backend/scripts/build_seed.py dựng, chỉ gồm các bảng nội dung.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

MARKER = "base_seed"
# bảng có cột identity cần chỉnh lại sequence sau khi nạp id có sẵn
IDENTITY = {
    "subjects": "subject_id",
    "chapters": "chapter_id",
    "questions": "question_id",
    "statements": "statement_id",
    "exams": "exam_id",
    "sections": "section_id",
    "media": "media_id",
}


def dsn() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main() -> int:
    content = Path(os.environ.get("SEED_DIR", "/seed")) / "content"
    manifest_path = content / "manifest.json"
    if not manifest_path.exists():
        print("[seed] Không có gói dữ liệu nền, bỏ qua (chỉ tạo bảng).")
        return 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    conn = await asyncpg.connect(dsn())
    try:
        if await conn.fetchval("SELECT 1 FROM app_init_state WHERE key = $1", MARKER):
            print("[seed] Đã nạp dữ liệu nền trước đó, bỏ qua.")
            return 0
        counts: dict[str, int] = {}
        async with conn.transaction():
            await conn.execute("SET LOCAL TIME ZONE 'UTC'")
            for table in manifest["tables"]:
                name, cols = table["name"], table["columns"]
                await conn.copy_to_table(
                    name,
                    source=str(content / f"{name}.csv"),
                    columns=cols,
                    format="csv",
                    null=r"\N",
                    encoding="utf-8",
                )
                counts[name] = await conn.fetchval(f'SELECT count(*) FROM "{name}"')
                expected = table["rows"]
                if counts[name] != expected:
                    raise RuntimeError(f"{name}: nạp {counts[name]} dòng, gói có {expected}")
                print(f"[seed] {name}: {counts[name]} dòng")
            for name, pk in IDENTITY.items():
                await conn.execute(
                    f"SELECT setval(pg_get_serial_sequence('{name}', '{pk}'), "
                    f'COALESCE((SELECT max("{pk}") FROM "{name}"), 1), '
                    f'(SELECT max("{pk}") FROM "{name}") IS NOT NULL)'
                )
            await conn.execute(
                "INSERT INTO app_init_state (key, detail) VALUES ($1, $2)",
                MARKER,
                json.dumps({"built_at": manifest.get("built_at"), "rows": counts}),
            )
        print("[seed] Hoàn tất.")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
