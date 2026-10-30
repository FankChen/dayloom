from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from dayloom.db import CalendarEvent, Preference, Task
from dayloom.schemas import Preferences


def preferences_for(session) -> Preferences:
    stored = session.get(Preference, "planning")
    return Preferences.model_validate(stored.value if stored else {})


def build_plan(session, day: date, now: datetime | None = None) -> dict:
    preferences = preferences_for(session)
    zone = ZoneInfo(preferences.timezone)
    start = datetime.combine(day, time(preferences.work_start), zone)
    end = datetime.combine(day, time(preferences.work_end), zone)
    current = (now or datetime.now(zone)).astimezone(zone)
    if day == current.date():
        start = max(start, current.replace(second=0, microsecond=0) + timedelta(minutes=1))
    if day < current.date():
        start = end
    intervals = [(start, end)] if start < end else []
    calendar = []
    for event in session.scalars(select(CalendarEvent).order_by(CalendarEvent.start)):
        event_start = datetime.fromisoformat(event.start).astimezone(zone)
        event_end = datetime.fromisoformat(event.end).astimezone(zone)
        if event_start.date() <= day <= event_end.date() and event_end > datetime.combine(
            day, time(), zone
        ):
            calendar.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "start": event.start,
                    "end": event.end,
                    "source": event.source,
                }
            )
        remaining = []
        for free_start, free_end in intervals:
            if event_end <= free_start or event_start >= free_end:
                remaining.append((free_start, free_end))
            else:
                if free_start < event_start:
                    remaining.append((free_start, event_start))
                if event_end < free_end:
                    remaining.append((event_end, free_end))
        intervals = remaining

    priority_order = {"high": 0, "normal": 1, "low": 2}
    tasks = list(session.scalars(select(Task).where(Task.status.in_(["ready", "doing"]))))
    tasks.sort(
        key=lambda task: (
            task.due_date is None or task.due_date > day.isoformat(),
            task.due_date or "9999-12-31",
            priority_order[task.priority],
            task.created_at,
            task.id,
        )
    )
    available = int(
        sum((free_end - free_start).total_seconds() / 60 for free_start, free_end in intervals)
    )
    budget = min(available, preferences.daily_minutes)
    items = []
    deferred = []
    for task in tasks:
        slot = next(
            (
                index
                for index, (free_start, free_end) in enumerate(intervals)
                if (free_end - free_start).total_seconds() >= task.minutes * 60
            ),
            None,
        )
        if len(items) >= preferences.focus_count or budget < task.minutes or slot is None:
            deferred.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "reason": "Outside today's focus or available time",
                }
            )
            continue
        free_start, free_end = intervals[slot]
        task_end = free_start + timedelta(minutes=task.minutes)
        intervals[slot] = (task_end, free_end)
        budget -= task.minutes
        reason = (
            "Due today or overdue"
            if task.due_date and task.due_date <= day.isoformat()
            else "Priority and available time"
        )
        items.append(
            {
                "task_id": task.id,
                "title": task.title,
                "start": free_start.isoformat(),
                "end": task_end.isoformat(),
                "minutes": task.minutes,
                "reason": reason,
                "source": task.source,
                "priority": task.priority,
            }
        )
    deadlines = [
        {"task_id": task.id, "title": task.title, "due_date": task.due_date}
        for task in tasks
        if task.due_date and task.due_date <= (day + timedelta(days=3)).isoformat()
    ]
    return {
        "day": day.isoformat(),
        "timezone": preferences.timezone,
        "items": items,
        "deferred": deferred,
        "deadlines": deadlines,
        "calendar": calendar,
        "available_minutes": available,
        "capacity_minutes": min(available, preferences.daily_minutes),
        "planned_minutes": sum(item["minutes"] for item in items),
        "strategy": "Rules baseline: deadlines, priority, free calendar slots",
    }
