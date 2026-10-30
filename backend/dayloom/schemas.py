from datetime import date
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=5000)
    priority: Literal["high", "normal", "low"] = "normal"
    minutes: int = Field(default=30, ge=5, le=480)
    due_date: date | None = None


class TaskUpdate(TaskInput):
    status: Literal["ready", "doing", "blocked", "done"] = "ready"
    version: int = Field(ge=1)


class MemoryInput(StrictModel):
    content: str = Field(min_length=1, max_length=3000)
    category: Literal["preference", "goal", "fact", "context"] = "preference"
    expires_on: date | None = None


class MemoryUpdate(MemoryInput):
    version: int = Field(ge=1)


class BriefInput(StrictModel):
    day: date


class Proposal(StrictModel):
    tool: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any]


class ModelReply(StrictModel):
    message: str = Field(min_length=1, max_length=10000)
    proposals: list[Proposal] = Field(default_factory=list, max_length=5)


class ChatInput(StrictModel):
    content: str = Field(min_length=1, max_length=10000)
    allow_external: bool = False


class Approval(StrictModel):
    digest: str = Field(min_length=64, max_length=64)


class ActionUpdate(Approval):
    payload: dict[str, Any]


class CalendarImport(StrictModel):
    content: str = Field(min_length=1, max_length=500000)
    source: str = Field(default="Imported calendar", min_length=1, max_length=100)


class Preferences(StrictModel):
    timezone: str = "Asia/Shanghai"
    daily_minutes: int = Field(default=180, ge=15, le=720)
    work_start: int = Field(default=9, ge=0, le=22)
    work_end: int = Field(default=18, ge=1, le=23)
    focus_count: int = Field(default=3, ge=1, le=5)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Unknown IANA timezone") from error
        return value

    @model_validator(mode="after")
    def valid_work_hours(self):
        if self.work_end <= self.work_start:
            raise ValueError("Working hours must end after they start")
        return self
