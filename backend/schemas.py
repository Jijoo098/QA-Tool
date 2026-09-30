"""Shapes of JSON the API accepts and returns.

Pydantic checks this data before it is saved. Invalid values are rejected
with a 422 response instead of being written to the database.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Allowed values. Anything else is rejected.
TestType = Literal["positive", "negative", "edge"]
Priority = Literal["High", "Medium", "Low"]
Status = Literal["Draft", "Approved"]


def _required_text(value: str) -> str:
    """Trim a required string and reject blanks."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be blank")
    return cleaned


def _optional_text(value: str | None) -> str | None:
    """Trim an optional string. Blank becomes None."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _required_text(value)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return _optional_text(value)


class ProjectUpdate(ProjectCreate):
    """Same fields as create. A PUT replaces the whole project."""


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RequirementCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _required_text(value)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return _optional_text(value)


class RequirementUpdate(RequirementCreate):
    """Same fields as create. A PUT replaces the whole requirement."""


class RequirementOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TestCaseCreate(BaseModel):
    requirement_id: int
    title: str = Field(min_length=1, max_length=200)
    type: TestType
    preconditions: str | None = Field(default=None, max_length=10000)
    steps: str | None = Field(default=None, max_length=10000)
    expected_result: str | None = Field(default=None, max_length=10000)
    priority: Priority
    status: Status = "Draft"

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _required_text(value)

    @field_validator("preconditions", "steps", "expected_result")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        return _optional_text(value)


class TestCaseUpdate(TestCaseCreate):
    """Same fields as create. A PUT replaces the whole test case."""


class TestCaseOut(BaseModel):
    id: int
    requirement_id: int
    title: str
    type: TestType
    preconditions: str | None
    steps: str | None
    expected_result: str | None
    priority: Priority
    status: Status
    created_at: datetime

    model_config = {"from_attributes": True}
