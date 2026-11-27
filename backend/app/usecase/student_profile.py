from app.models.student import StudentProfile
from app.models.user import User
from app.repositories.credits import CREDIT_LIMIT, DAILY_CREDITS, CreditRepository
from app.repositories.student_profiles import StudentProfileRepository
from app.schemas.student import CreditEntryOut, CreditsOut, ProfileIn, ProfileOut, ProfileStatusOut


class UnverifiedReminderEmail(Exception):
    pass


class StudentProfileUseCase:
    def __init__(self, profiles: StudentProfileRepository, credits: CreditRepository) -> None:
        self._profiles = profiles
        self._credits = credits

    async def get(self, user: User) -> ProfileStatusOut:
        profile, days = await self._profiles.get_with_days(user.user_id)
        return ProfileStatusOut(
            completed=profile is not None,
            profile=self._output(user, profile, days) if profile else None,
            email_verified=user.email_verified_at is not None,
        )

    async def save(self, user: User, body: ProfileIn) -> ProfileOut:
        if body.reminder_time is not None and user.email_verified_at is None:
            raise UnverifiedReminderEmail()
        values = body.model_dump(exclude={"study_days", "display_name"})
        profile = await self._profiles.save(user, values, body.study_days, body.display_name)
        return self._output(user, profile, body.study_days)

    @staticmethod
    def _output(user: User, profile: StudentProfile, days: list[int]) -> ProfileOut:
        return ProfileOut(
            school_name=profile.school_name, grade=profile.grade, target_score=profile.target_score,
            exam_period=profile.exam_period, reminder_time=profile.reminder_time, study_days=days,
            display_name=user.display_name, email=user.email, email_verified=user.email_verified_at is not None,
            joined_at=user.created_at,
        )

    async def credits(self, user_id: int, before_id: int | None, limit: int) -> CreditsOut:
        balance = await self._credits.balance(user_id)
        entries = await self._credits.history(user_id, before_id, limit + 1)
        history = [CreditEntryOut.model_validate(entry) for entry in entries[:limit]]
        return CreditsOut(
            balance=balance, limit=CREDIT_LIMIT, daily_grant=DAILY_CREDITS, history=history,
            next_before_id=history[-1].id if len(entries) > limit else None,
        )
