"""Dựng gói dữ liệu nền (chạy trên MÁY NHÓM, không chạy trên VPS).

Đọc bản backup (dump MySQL + tar MinIO), chỉ giữ:
  - các bảng NỘI DUNG trong ALLOWED_TABLES (không có users, students, parents, thanh toán, token…)
  - các tệp MinIO mà media được nội dung tham chiếu (`![media:ID](media:ID)`)
và ghi ra thư mục đầu ra:
  content/<bảng>.csv  + content/manifest.json
  minio/<bucket>/<object_key>

Cần: Docker (chạy MySQL tạm trên tmpfs), `pip install -r backend/requirements-seed.txt`.
Ví dụ:
  python backend/scripts/build_seed.py --backup data/private/bee-clone-... --out data/private/seed
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pymysql

CONTAINER = "examind-seed-mysql"
MYSQL_PASSWORD = "seed"
MYSQL_PORT = 33306
DATABASE = "beedatabase"

# Thứ tự nạp (cha trước con). Mọi bảng khác bị bỏ.
ALLOWED_TABLES = [
    "subjects",
    "chapters",
    "questions",
    "statements",
    "questions_chapters",
    "exams",
    "sections",
    "questions_exams",
    "media",
]
# Cột trỏ tới người dùng hoặc dữ liệu không cần: ghi NULL.
NULLIFY = {
    "questions": {"created_by"},
    "exams": {"created_by"},
    "media": {"folder_id", "uploaded_by", "raw_content"},
}
# Cột văn bản có thể chứa tham chiếu ảnh.
MEDIA_REF_COLUMNS = {
    "questions": ["content", "searchable_content", "correct_answer", "solution"],
    "statements": ["content"],
    "exams": ["description"],
    "sections": ["description"],
}
MEDIA_REF = re.compile(r"media:(\d+)")


def sh(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, **kw)


def start_mysql() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
    sh(
        "docker", "run", "-d", "--name", CONTAINER,
        "-e", f"MYSQL_ROOT_PASSWORD={MYSQL_PASSWORD}", "-e", f"MYSQL_DATABASE={DATABASE}",
        "--tmpfs", "/var/lib/mysql", "-p", f"127.0.0.1:{MYSQL_PORT}:3306",
        "mysql:8.0", "--character-set-server=utf8mb4", "--skip-log-bin",
        capture_output=True,
    )
    for _ in range(90):
        try:
            conn = pymysql.connect(host="127.0.0.1", port=MYSQL_PORT, user="root", password=MYSQL_PASSWORD)
            conn.close()
            return
        except pymysql.err.OperationalError:
            time.sleep(2)
    raise SystemExit("MySQL tạm không khởi động được")


def restore_dump(dump: Path) -> None:
    print("Khôi phục dump vào MySQL tạm…", flush=True)
    proc = subprocess.Popen(
        ["docker", "exec", "-i", CONTAINER, "mysql", f"-uroot", f"-p{MYSQL_PASSWORD}", DATABASE],
        stdin=subprocess.PIPE,
    )
    with gzip.open(dump, "rb") as src:
        shutil.copyfileobj(src, proc.stdin, 1024 * 1024)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("Khôi phục dump lỗi")


def cell(value) -> str:
    if value is None:
        return r"\N"
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S") + "+00"
    return str(value).replace("\x00", "")


def export_tables(out: Path) -> dict:
    content = out / "content"
    content.mkdir(parents=True, exist_ok=True)
    conn = pymysql.connect(
        host="127.0.0.1", port=MYSQL_PORT, user="root", password=MYSQL_PASSWORD,
        database=DATABASE, charset="utf8mb4", cursorclass=pymysql.cursors.SSCursor,
    )
    referenced: set[int] = set()
    manifest: dict = {"tables": [], "built_at": datetime.now(timezone.utc).isoformat()}
    cur = conn.cursor()

    def fetch(table: str, where: str = ""):
        cur.execute(f"SELECT * FROM `{table}` {where}")
        return [d[0] for d in cur.description]

    for table in ALLOWED_TABLES:
        if table == "media":
            # Nạp sau cùng: chỉ giữ media được tham chiếu và chuỗi parent của chúng.
            continue
        cols = fetch(table)
        nul = NULLIFY.get(table, set())
        ref_idx = [cols.index(c) for c in MEDIA_REF_COLUMNS.get(table, []) if c in cols]
        path = content / f"{table}.csv"
        n = 0
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for row in cur:
                for i in ref_idx:
                    if isinstance(row[i], str):
                        referenced.update(int(m) for m in MEDIA_REF.findall(row[i]))
                w.writerow([cell(None if c in nul else v) for c, v in zip(cols, row)])
                n += 1
        manifest["tables"].append({"name": table, "columns": cols, "rows": n})
        print(f"  {table}: {n} dòng", flush=True)

    # media: đóng bao theo parent_id
    cur2 = conn.cursor()
    wanted = set(referenced)
    while True:
        if not wanted:
            break
        ids = ",".join(str(i) for i in sorted(wanted))
        cur2.execute(f"SELECT media_id, parent_id FROM media WHERE media_id IN ({ids})")
        parents = {p for _, p in cur2.fetchall() if p and p not in wanted}
        if not parents:
            break
        wanted |= parents
    ids_sql = ",".join(str(i) for i in sorted(wanted)) or "NULL"
    cols = fetch("media", f"WHERE media_id IN ({ids_sql}) ORDER BY media_id")
    nul = NULLIFY["media"]
    rows = 0
    objects: set[tuple[str, str]] = set()
    b_idx, k_idx = cols.index("bucket_name"), cols.index("object_key")
    found_ids: set[int] = set()
    with open(content / "media.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in cur:
            objects.add((row[b_idx], row[k_idx]))
            found_ids.add(row[cols.index("media_id")])
            w.writerow([cell(None if c in nul else v) for c, v in zip(cols, row)])
            rows += 1
    manifest["tables"].append({"name": "media", "columns": cols, "rows": rows})
    print(f"  media: {rows} dòng (được tham chiếu {len(referenced)} id)", flush=True)
    missing_rows = sorted(referenced - found_ids)
    manifest["media_ids_without_row"] = missing_rows
    if missing_rows:
        print(f"  CẢNH BÁO: {len(missing_rows)} id media được tham chiếu nhưng không có dòng trong bảng media", flush=True)
    conn.close()
    manifest["objects_wanted"] = len(objects)
    (content / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"objects": objects, "manifest": manifest}


def extract_objects(tar_path: Path, out: Path, objects: set[tuple[str, str]]) -> tuple[int, int, list[str]]:
    wanted = {f"{b}/{k}" for b, k in objects}
    dest = out / "minio"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    found, size = set(), 0
    print(f"Quét tar MinIO (cần {len(wanted)} đối tượng)…", flush=True)
    with tarfile.open(tar_path, "r|gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            name = member.name[2:] if member.name.startswith("./") else member.name
            if name not in wanted:
                continue
            target = (dest / name).resolve()
            if dest.resolve() not in target.parents:
                continue  # chặn đường dẫn thoát khỏi thư mục đích
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tar.extractfile(member)
            with open(target, "wb") as f:
                shutil.copyfileobj(src, f)
            found.add(name)
            size += member.size
            if len(found) == len(wanted):
                break
    return len(found), size, sorted(wanted - found)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--keep-mysql", action="store_true")
    args = ap.parse_args()
    dump, tar_path = args.backup / "mysql.sql.gz", args.backup / "minio-objects.tar.gz"
    for p in (dump, tar_path):
        if not p.exists():
            print(f"Thiếu {p}")
            return 1
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        start_mysql()
        restore_dump(dump)
        print("Xuất bảng nội dung:", flush=True)
        result = export_tables(args.out)
    finally:
        if not args.keep_mysql:
            subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
    got, size, missing = extract_objects(tar_path, args.out, result["objects"])
    print(f"Đã lấy {got}/{len(result['objects'])} đối tượng MinIO, {size / 1e6:.1f} MB")
    summary = {"objects_found": got, "objects_missing": missing, "bytes": size}
    manifest = result["manifest"]
    manifest["minio"] = summary
    (args.out / "content" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if missing:
        print(f"CẢNH BÁO: thiếu {len(missing)} đối tượng trong tar (xem manifest.json), ví dụ: {missing[:3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
