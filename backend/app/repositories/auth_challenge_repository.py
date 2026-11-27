from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_challenge import EmailChallenge, GoogleHandoff


class AuthChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_email(self, purpose: str, email: str) -> EmailChallenge:
        # Create the rate-limit row once, even when two requests arrive together.
        insert = sqlite_insert if self._session.get_bind().dialect.name == "sqlite" else postgres_insert
        await self._session.execute(
            insert(EmailChallenge)
            .values(purpose=purpose, email=email)
            .on_conflict_do_nothing(index_elements=["purpose", "email"])
        )
        query = select(EmailChallenge).where(EmailChallenge.purpose == purpose, EmailChallenge.email == email)
        return (await self._session.execute(query.with_for_update())).scalar_one()

    async def lock_existing_email(self, purpose: str, email: str) -> EmailChallenge | None:
        query = select(EmailChallenge).where(EmailChallenge.purpose == purpose, EmailChallenge.email == email)
        return (await self._session.execute(query.with_for_update())).scalar_one_or_none()

    async def lock_challenge(self, purpose: str, digest: str) -> EmailChallenge | None:
        query = select(EmailChallenge).where(
            EmailChallenge.purpose == purpose, EmailChallenge.challenge_hash == digest
        )
        return (await self._session.execute(query.with_for_update())).scalar_one_or_none()

    async def delete_stale_challenges(self, before: datetime) -> None:
        await self._session.execute(delete(EmailChallenge).where(EmailChallenge.window_start < before))

    async def save_handoff(
        self, digest: str, browser_challenge: str, payload: dict, expires_at: datetime, now: datetime
    ) -> None:
        await self._session.execute(delete(GoogleHandoff).where(GoogleHandoff.expires_at <= now))
        self._session.add(
            GoogleHandoff(
                ticket_hash=digest, browser_challenge=browser_challenge, payload=payload, expires_at=expires_at
            )
        )
        await self._session.commit()

    async def take_handoff(self, digest: str, browser_challenge: str, now: datetime) -> dict | None:
        query = (
            delete(GoogleHandoff)
            .where(
                GoogleHandoff.ticket_hash == digest,
                GoogleHandoff.browser_challenge == browser_challenge,
                GoogleHandoff.expires_at > now,
            )
            .returning(GoogleHandoff.payload)
        )
        return (await self._session.execute(query)).scalar_one_or_none()

    async def commit(self) -> None:
        await self._session.commit()
