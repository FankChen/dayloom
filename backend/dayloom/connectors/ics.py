import hashlib
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar

from dayloom.registry import connectors


@connectors.register
class IcsCalendar:
    label = "Calendar file"

    def read(self, content: str, source: str, timezone: str, today: date) -> list[dict]:
        calendar = Calendar.from_ical(content)
        zone = ZoneInfo(timezone)
        start = datetime.combine(today - timedelta(days=1), time(), zone)
        end = start + timedelta(days=33)
        occurrences = recurring_ical_events.of(calendar).between(start, end)
        if len(occurrences) > 500:
            raise ValueError("Import at most 500 calendar occurrences at a time")
        events = {}
        for occurrence in occurrences:
            if str(occurrence.get("STATUS", "")).upper() == "CANCELLED":
                continue
            raw_start = occurrence.decoded("DTSTART")
            raw_end = occurrence.decoded("DTEND", raw_start + timedelta(days=1))
            event_start = self._normalize(raw_start, zone)
            event_end = self._normalize(raw_end, zone)
            if event_end <= event_start:
                continue
            uid = str(occurrence.get("UID", ""))
            title = str(occurrence.get("SUMMARY", "Busy"))[:200]
            signature = f"{source}|{uid or title}|{event_start.isoformat()}"
            identifier = hashlib.sha256(signature.encode()).hexdigest()
            events[identifier] = {
                "id": identifier,
                "title": title,
                "start": event_start.isoformat(),
                "end": event_end.isoformat(),
                "source": source,
            }
        return list(events.values())

    @staticmethod
    def _normalize(value: date | datetime, zone: ZoneInfo) -> datetime:
        if not isinstance(value, datetime):
            value = datetime.combine(value, time(), zone)
        elif value.tzinfo is None:
            value = value.replace(tzinfo=zone)
        return value.astimezone(UTC)
