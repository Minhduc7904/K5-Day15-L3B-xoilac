"""Kiểm tay socket và thống kê online (#20) trên backend đang chạy.

    cd backend
    SMOKE_ADMIN_EMAIL=admin@example.com SMOKE_ADMIN_PASSWORD='...' python scripts/socket_smoke.py [--base http://localhost:8000]

Cần backend chạy với một admin (vd admin gốc do ensure_admin tạo) và thư viện aiohttp (requirements-dev.txt).
Admin tạo hai học sinh mới qua POST /admin/users (email, mật khẩu ngẫu nhiên; không cần dịch vụ email
như đăng ký công khai), học sinh đăng nhập, rồi đi kịch bản:
  A mở 2 kết nối, B mở 1 → thống kê 2 học sinh / 3 kết nối
  đóng 2 kết nối của A → 1 / 1
  dùng lại một ticket → bị từ chối
  admin khoá B → B nhận session:revoked {reason: disabled}, thống kê về 0 / 0
  A mở kết nối mới rồi đăng xuất → A nhận session:revoked {reason: logout}
Không in mật khẩu hay token. Thoát mã 0 nếu mọi bước đạt.
"""
import argparse
import asyncio
import os
import secrets
import sys
import time

import httpx
import socketio

SOCKET_PATH = "/api/socket.io"
results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'ĐẠT' if ok else 'LỖI'}] {name}{(' - ' + detail) if detail else ''}", flush=True)


async def wait_for(predicate, timeout: float = 5.0) -> float | None:
    """Chờ tới khi predicate() đúng; trả số giây đã chờ, hoặc None nếu quá hạn."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if predicate():
            return time.monotonic() - start
        await asyncio.sleep(0.05)
    return None


class Conn:
    def __init__(self, label: str) -> None:
        self.label = label
        self.client = socketio.AsyncClient(reconnection=False)
        self.revoked: list = []
        self.refused: list = []
        self.client.on("session:revoked", lambda data: self.revoked.append(data))
        self.client.on("connect_error", lambda data: self.refused.append(data))

    async def open(self, base: str, ticket: str) -> bool:
        try:
            await self.client.connect(
                base, socketio_path=SOCKET_PATH, transports=["websocket"], auth={"ticket": ticket}, wait_timeout=5
            )
            return True
        except socketio.exceptions.ConnectionError:
            return False


class Api:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.http = http

    async def create_student(self, admin: str, email: str, password: str) -> None:
        r = await self.http.post("/api/v1/admin/users", json={"email": email, "password": password}, headers=self.h(admin))
        r.raise_for_status()

    async def login(self, email: str, password: str) -> str:
        r = await self.http.post("/api/v1/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        self.http.cookies.clear()
        return r.cookies["examind_session"]

    @staticmethod
    def h(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def ticket(self, token: str) -> str:
        r = await self.http.post("/api/v1/auth/socket-ticket", headers=self.h(token))
        r.raise_for_status()
        return r.json()["ticket"]

    async def stats(self, admin: str) -> tuple[int, int]:
        r = await self.http.get("/api/v1/admin/stats/online-students", headers=self.h(admin))
        r.raise_for_status()
        return r.json()["online_students"], r.json()["connections"]

    async def me(self, token: str) -> dict:
        r = await self.http.get("/api/v1/auth/me", headers=self.h(token))
        return r.json()


async def main(base: str, admin_email: str, admin_password: str) -> int:
    tag = secrets.token_hex(3)
    email_a, email_b = f"smoke-a-{tag}@example.com", f"smoke-b-{tag}@example.com"
    async with httpx.AsyncClient(base_url=base, timeout=10) as http:
        api = Api(http)
        admin = await api.login(admin_email, admin_password)
        pw_a, pw_b = "T-" + secrets.token_urlsafe(16), "T-" + secrets.token_urlsafe(16)
        await api.create_student(admin, email_a, pw_a)
        await api.create_student(admin, email_b, pw_b)
        token_a = await api.login(email_a, pw_a)
        token_b = await api.login(email_b, pw_b)
        print(f"Học sinh A={email_a}, B={email_b}; admin={admin_email} (mật khẩu, token: ***)")
        before = await api.stats(admin)
        print(f"Thống kê trước kịch bản: {before[0]} học sinh, {before[1]} kết nối")

        a1, a2, b1 = Conn("A1"), Conn("A2"), Conn("B1")
        ticket_a1 = await api.ticket(token_a)
        ok = await a1.open(base, ticket_a1) and await a2.open(base, await api.ticket(token_a))
        ok = ok and await b1.open(base, await api.ticket(token_b))
        now = await api.stats(admin)
        step("A mở 2 kết nối, B mở 1", ok and now == (before[0] + 2, before[1] + 3), f"thống kê {now[0]} học sinh, {now[1]} kết nối")

        await a1.client.disconnect()
        await a2.client.disconnect()
        await asyncio.sleep(0.3)
        now = await api.stats(admin)
        step("Đóng 2 kết nối của A", now == (before[0] + 1, before[1] + 1), f"thống kê {now[0]} học sinh, {now[1]} kết nối")

        reuse = Conn("A-reuse")
        refused = not await reuse.open(base, ticket_a1)
        # Server từ chối handshake bằng connect_error chung (không có mã lỗi riêng).
        step("Dùng lại ticket đã dùng", refused and bool(reuse.refused), f"bị từ chối: {reuse.refused[0] if reuse.refused else '-'}")

        b_id = (await api.me(token_b))["user_id"]
        r = await http.patch(f"/api/v1/admin/users/{b_id}", json={"status": "disabled"}, headers=api.h(admin))
        waited = await wait_for(lambda: bool(b1.revoked) and not b1.client.connected)
        now = await api.stats(admin)
        step(
            "Admin khoá B",
            r.status_code == 200 and waited is not None and b1.revoked == [{"reason": "disabled"}] and now == before,
            f"PATCH {r.status_code}; B nhận {b1.revoked} sau {waited:.2f} s; thống kê {now[0]} học sinh, {now[1]} kết nối"
            if waited is not None else f"PATCH {r.status_code}; B không nhận session:revoked",
        )

        a3 = Conn("A3")
        opened = await a3.open(base, await api.ticket(token_a))
        r = await http.post("/api/v1/auth/logout", headers=api.h(token_a))
        waited = await wait_for(lambda: bool(a3.revoked) and not a3.client.connected)
        step(
            "A đăng xuất",
            opened and r.status_code == 204 and waited is not None and a3.revoked == [{"reason": "logout"}],
            f"logout {r.status_code}; A nhận {a3.revoked} sau {waited:.2f} s" if waited is not None else f"logout {r.status_code}; A không nhận session:revoked",
        )
        final = await api.stats(admin)
        print(f"Thống kê sau kịch bản: {final[0]} học sinh, {final[1]} kết nối")

    failed = [name for name, ok, _ in results if not ok]
    print(f"Kết quả: {len(results) - len(failed)}/{len(results)} bước đạt")
    return 1 if failed else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Kiểm tay socket và thống kê online (#20).")
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    email, password = os.environ.get("SMOKE_ADMIN_EMAIL"), os.environ.get("SMOKE_ADMIN_PASSWORD")
    if not email or not password:
        sys.exit("Cần SMOKE_ADMIN_EMAIL và SMOKE_ADMIN_PASSWORD (không truyền mật khẩu qua tham số).")
    sys.exit(asyncio.run(main(args.base, email, password)))
