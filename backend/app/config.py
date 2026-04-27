from datetime import timedelta


def _parse_interval_label(value: str) -> timedelta:
    cleaned = value.strip().lower()
    if cleaned.endswith("h"):
        return timedelta(hours=int(cleaned[:-1]))
    if cleaned.endswith("d"):
        return timedelta(days=int(cleaned[:-1]))
    raise ValueError(f"Unsupported schedule interval label: {value}")


SCHEDULE_INTERVAL_LABELS = ("1h", "3h", "6h", "12h", "1d", "3d", "7d", "14d", "30d", "60d")
SCHEDULE_INTERVALS = [(label, _parse_interval_label(label)) for label in SCHEDULE_INTERVAL_LABELS]
FULL_CREDIT_TOLERANCE = 1.0e-9

FORCED_UNORDERED_PROMPTS = {
    ("geography/rivers", "name the two rivers that meet in khartoum."),
    ("geography/rivers", "name two rivers that flow through germany."),
}
