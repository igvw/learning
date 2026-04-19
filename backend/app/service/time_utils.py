from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..config import FULL_CREDIT_TOLERANCE


def parse_iso_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def add_interval_to_timestamp(value: str, interval: timedelta) -> str:
    return (parse_iso_timestamp(value) + interval).isoformat()


def schedule_due_at(value: str, interval: timedelta, *, timezone: ZoneInfo) -> str:
    if interval < timedelta(days=1):
        return add_interval_to_timestamp(value, interval)

    answered_at = parse_iso_timestamp(value)
    answered_local = answered_at.astimezone(timezone)
    due_date = answered_local.date() + timedelta(days=interval.days)
    due_at = datetime.combine(due_date, time.min, tzinfo=timezone)
    return due_at.isoformat()


def is_full_credit(score_earned: float | None, score_possible: float | None) -> bool:
    if score_earned is None or score_possible is None or score_possible <= 0:
        return False
    return score_earned >= (score_possible - FULL_CREDIT_TOLERANCE)
