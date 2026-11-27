from datetime import date, datetime
from zoneinfo import ZoneInfo

STUDY_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def study_date(instant: datetime) -> date:
    return instant.astimezone(STUDY_TZ).date()
