"""Run the student maintenance jobs independently of the API server."""
import argparse
import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.core.config import get_settings
from app.core.database import get_engine, get_sessionmaker
from app.service.email_service import GmailEmailService
from app.usecase.student_jobs import DailyCreditJob, StudyReminderJob

log = logging.getLogger(__name__)
JOB_NAMES = ("daily-credit", "study-reminders")
POLL_SECONDS = 30


async def run_job(name: str, job: Callable[[], Awaitable[dict[str, int]]], once: bool) -> None:
    while True:
        try:
            result = await job()
            if once or any(result.values()):
                log.info("%s %s", name, result)
        except Exception as error:
            log.error("%s failed (%s)", name, type(error).__name__)
            if once:
                raise
        if once:
            return
        await asyncio.sleep(POLL_SECONDS)


async def main(once: bool, selected: str | None) -> None:
    settings = get_settings()
    sessions = get_sessionmaker()
    jobs = {"daily-credit": DailyCreditJob(sessions).run}
    if settings.email_provider == "gmail":
        jobs["study-reminders"] = StudyReminderJob(
            sessions, GmailEmailService(settings), settings.frontend_url
        ).run
    if "study-reminders" not in jobs:
        if selected == "study-reminders":
            raise SystemExit("study-reminders requires EMAIL_PROVIDER=gmail")
        log.info("study-reminders disabled (EMAIL_PROVIDER is not gmail)")
    log.info("Student worker started")
    try:
        await asyncio.gather(*(run_job(name, job, once) for name, job in jobs.items() if not selected or name == selected))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--job", choices=JOB_NAMES)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(main(args.once, args.job))
    except KeyboardInterrupt:
        pass
