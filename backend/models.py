"""Database tables for the test case manager.

A project has many requirements.
A requirement has many test cases.
Deleting a parent also deletes its children (see cascade on the relationships).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    """Current time in UTC. Used as the default for created_at."""
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # cascade deletes requirements (and their test cases) when a project is deleted
    requirements = relationship(
        "Requirement",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("Project", back_populates="requirements")
    test_cases = relationship(
        "TestCase",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(
        Integer, ForeignKey("requirements.id"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False)  # positive, negative, or edge
    preconditions = Column(Text, nullable=True)
    steps = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=True)
    priority = Column(String(20), nullable=False)  # High, Medium, or Low
    status = Column(String(20), nullable=False, default="Draft")  # Draft or Approved
    created_at = Column(DateTime, default=utcnow)

    requirement = relationship("Requirement", back_populates="test_cases")
