"""Test đơn vị cho realtime (#20): SocketTicketService, InMemoryPresenceRegistry, RealtimeUseCase với đối tượng giả.
Không cần socket thật, không cần DB."""
import pytest

from app.service.presence_service import InMemoryPresenceRegistry, OnlineUser
from app.service.socket_ticket_service import SocketTicketService, TicketClaim
from app.usecase.auth import AccountDisabled, CurrentUser, SessionExpired, SessionRevoked
from app.usecase.realtime import RealtimeUseCase, TicketInvalid, TicketMissing


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


# ---- SocketTicketService ----------------------------------------------------------------


def test_ticket_is_single_use_and_bound_to_session():
    svc = SocketTicketService(ttl_seconds=30, clock=FakeClock())
    t = svc.issue(user_id=7, session_id=42)
    assert svc.redeem(t) == TicketClaim(user_id=7, session_id=42)
    assert svc.redeem(t) is None  # dùng lần hai


def test_ticket_expires_after_ttl():
    clock = FakeClock()
    svc = SocketTicketService(ttl_seconds=30, clock=clock)
    t1, t2 = svc.issue(1, 1), svc.issue(1, 1)
    clock.now += 29.9
    assert svc.redeem(t1) is not None
    clock.now += 0.2  # 30,1 s sau khi phát
    assert svc.redeem(t2) is None


def test_unknown_ticket_rejected_and_tickets_are_distinct():
    svc = SocketTicketService(clock=FakeClock())
    assert svc.redeem("khong-phai-ticket") is None
    assert svc.issue(1, 1) != svc.issue(1, 1)
    assert svc.ttl_seconds == 30


# ---- InMemoryPresenceRegistry --------------------------------------------------------------


async def test_two_tabs_one_student_then_offline():
    p = InMemoryPresenceRegistry()
    await p.connect("a1", user_id=1, role="student", session_id=10)
    await p.connect("a2", user_id=1, role="student", session_id=10)
    await p.connect("b1", user_id=2, role="student", session_id=20)
    await p.connect("adm", user_id=9, role="admin", session_id=90)
    assert await p.count_online_students() == (2, 3)  # admin không tính

    await p.disconnect("a1")
    assert await p.count_online_students() == (2, 2)
    await p.disconnect("a2")
    assert await p.count_online_students() == (1, 1)
    assert await p.sids_of_user(1) == []
    await p.disconnect("b1")
    assert await p.count_online_students() == (0, 0)
    assert await p.disconnect("khong-co") is None


async def test_sids_of_user_and_session_and_listing():
    p = InMemoryPresenceRegistry()
    await p.connect("s1", 1, "student", session_id=10)
    await p.connect("s2", 1, "student", session_id=11)  # cùng học sinh, phiên khác (máy khác)
    await p.connect("s3", 3, "student", session_id=30)
    assert await p.sids_of_user(1) == ["s1", "s2"]
    assert await p.sids_of_session(10) == ["s1"]
    assert await p.sids_of_session(11) == ["s2"]

    page, total = await p.list_online_students(offset=0, limit=1)
    assert total == 2 and page == [OnlineUser(user_id=1, connections=2)]
    page, _ = await p.list_online_students(offset=1, limit=10)
    assert page == [OnlineUser(user_id=3, connections=1)]


# ---- RealtimeUseCase với đối tượng giả -------------------------------------------------------


class FakeUser:
    def __init__(self, user_id: int, role: str) -> None:
        self.user_id, self.role = user_id, role


class FakeAuth:
    """Thay AuthUseCase: chỉ cần get_current_user_by_session."""

    def __init__(self) -> None:
        self.sessions: dict[int, CurrentUser | Exception] = {}

    async def get_current_user_by_session(self, session_id: int) -> CurrentUser:
        result = self.sessions.get(session_id, SessionRevoked())
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def rt():
    clock, auth, presence = FakeClock(), FakeAuth(), InMemoryPresenceRegistry()
    tickets = SocketTicketService(ttl_seconds=30, clock=clock)
    return RealtimeUseCase(tickets=tickets, presence=presence, auth=auth), auth, presence, clock


def _current(user_id: int, role: str, session_id: int) -> CurrentUser:
    return CurrentUser(user=FakeUser(user_id, role), session_id=session_id)


@pytest.mark.parametrize(("role", "rooms"), [("student", (("role", "student"), ("user", 5))), ("admin", (("role", "admin"), ("user", 5)))])
async def test_valid_ticket_admits_into_role_rooms(rt, role, rooms):
    usecase, auth, presence, _ = rt
    auth.sessions[50] = _current(5, role, 50)
    ticket, ttl = usecase.issue_ticket(_current(5, role, 50))
    assert ttl == 30

    admission = await usecase.admit(ticket, sid="sid-1")
    assert (admission.user_id, admission.role, admission.session_id, admission.rooms) == (5, role, 50, rooms)
    assert await presence.sids_of_session(50) == ["sid-1"]
    await usecase.leave("sid-1")
    assert await presence.sids_of_user(5) == []


@pytest.mark.parametrize("auth_payload", [None, {}, {"ticket": ""}, {"ticket": 123}])
async def test_missing_ticket_rejected(rt, auth_payload):
    usecase = rt[0]
    ticket = auth_payload.get("ticket") if isinstance(auth_payload, dict) else None
    with pytest.raises(TicketMissing):
        await usecase.admit(ticket, sid="x")


async def test_wrong_reused_and_expired_ticket_rejected(rt):
    usecase, auth, presence, clock = rt
    auth.sessions[50] = _current(5, "student", 50)
    with pytest.raises(TicketInvalid):
        await usecase.admit("ticket-sai", sid="x")

    ticket, _ = usecase.issue_ticket(_current(5, "student", 50))
    await usecase.admit(ticket, sid="x")
    with pytest.raises(TicketInvalid):  # dùng lần hai
        await usecase.admit(ticket, sid="y")

    late, _ = usecase.issue_ticket(_current(5, "student", 50))
    clock.now += 31
    with pytest.raises(TicketInvalid):
        await usecase.admit(late, sid="z")
    assert await presence.count_online_students() == (1, 1)  # chỉ kết nối hợp lệ đầu tiên


@pytest.mark.parametrize("error", [SessionRevoked(), SessionExpired(), AccountDisabled()])
async def test_session_revoked_expired_or_user_disabled_rejected(rt, error):
    usecase, auth, presence, _ = rt
    ticket, _ = usecase.issue_ticket(_current(5, "student", 50))
    auth.sessions[50] = error  # phiên bị thu hồi / hết hạn hoặc user bị khoá sau khi xin ticket
    with pytest.raises(type(error)):
        await usecase.admit(ticket, sid="x")
    assert await presence.count_online_students() == (0, 0)


async def test_ticket_for_other_user_rejected(rt):
    usecase, auth, _, _ = rt
    ticket, _ = usecase.issue_ticket(_current(5, "student", 50))
    auth.sessions[50] = _current(6, "student", 50)  # phiên giờ thuộc người khác (không thể xảy ra, vẫn chặn)
    with pytest.raises(TicketInvalid):
        await usecase.admit(ticket, sid="x")
