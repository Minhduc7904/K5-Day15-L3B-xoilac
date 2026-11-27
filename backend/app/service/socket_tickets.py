from collections import OrderedDict
from secrets import token_urlsafe
from time import monotonic
from collections.abc import Callable

TICKET_TTL_SECONDS = 30


class SocketTickets:
    """One-time tickets for a single backend process. Only session IDs are stored."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._tickets: OrderedDict[str, tuple[int, float]] = OrderedDict()

    def issue(self, session_id: int) -> str:
        now = self._clock()
        while self._tickets and next(iter(self._tickets.values()))[1] <= now:
            self._tickets.popitem(last=False)
        ticket = token_urlsafe(32)
        self._tickets[ticket] = (session_id, now + TICKET_TTL_SECONDS)
        return ticket

    def consume(self, ticket: str) -> int | None:
        entry = self._tickets.pop(ticket, None)
        if entry is None or entry[1] <= self._clock():
            return None
        return entry[0]
