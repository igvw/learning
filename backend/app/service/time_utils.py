from datetime import datetime, timedelta

from ..config import FULL_CREDIT_TOLERANCE


def parse_iso_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def add_interval_to_timestamp(value: str, interval: timedelta) -> str:
    return (parse_iso_timestamp(value) + interval).isoformat()


def is_full_credit(score_earned: float | None, score_possible: float | None) -> bool:
    if score_earned is None or score_possible is None or score_possible <= 0:
        return False
    return score_earned >= (score_possible - FULL_CREDIT_TOLERANCE)
