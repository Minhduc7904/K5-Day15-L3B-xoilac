from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import CreditAccount, CreditLedger

CREDIT_LIMIT = 500
DAILY_CREDITS = 100


class CreditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def open_account(self, user_id: int, day: date) -> None:
        account = CreditAccount(user_id=user_id, balance=CREDIT_LIMIT, last_daily_processed_on=day)
        self._session.add(account)
        await self._session.flush()
        self._record(account, CREDIT_LIMIT, "initial_grant", day)

    def _record(self, account: CreditAccount, delta: int, reason: str, day: date) -> None:
        self._session.add(CreditLedger(
            user_id=account.user_id, delta=delta, balance_after=account.balance, reason=reason, effective_on=day
        ))

    async def balance(self, user_id: int) -> int:
        # Keep the balance and paged ledger in one consistent view while the job updates this wallet.
        query = select(CreditAccount.balance).where(CreditAccount.user_id == user_id).with_for_update(read=True)
        balance = await self._session.scalar(query)
        if balance is None:
            raise LookupError("Missing student credit account")
        return balance

    async def history(self, user_id: int, before_id: int | None, limit: int):
        query = select(CreditLedger).where(CreditLedger.user_id == user_id)
        if before_id is not None:
            query = query.where(CreditLedger.id < before_id)
        return (await self._session.scalars(query.order_by(CreditLedger.id.desc()).limit(limit))).all()

    async def lock_due_accounts(self, day: date, limit: int):
        query = (
            select(CreditAccount)
            .where(CreditAccount.last_daily_processed_on < day)
            .order_by(CreditAccount.last_daily_processed_on, CreditAccount.user_id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self._session.scalars(query)).all()

    def apply_daily_grant(self, account: CreditAccount, day: date, amount: int) -> None:
        account.last_daily_processed_on = day
        if amount:
            account.balance += amount
            self._record(account, amount, "daily_grant", day)
