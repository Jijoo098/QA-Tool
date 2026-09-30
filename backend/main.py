"""Test Case Manager API.

Run from the qa-tool folder:
    uvicorn backend.main:app --reload
"""

import io
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

# HTML, CSS, and JS live next to the backend folder.
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables the first time the app starts. Safe to run again.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="QA Test Case Manager", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_requirement_or_404(db: Session, requirement_id: int) -> models.Requirement:
    requirement = db.get(models.Requirement, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement


def get_test_case_or_404(db: Session, test_case_id: int) -> models.TestCase:
    test_case = db.get(models.TestCase, test_case_id)
    if test_case is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case


def safe_filename(name: str) -> str:
    """Turn a project name into a simple ASCII download filename."""
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", name).strip("_")
    return cleaned or "project"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.post("/projects", response_model=schemas.ProjectOut, status_code=201)
def create_project(body: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = models.Project(name=body.name, description=body.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(models.Project).order_by(models.Project.id)).all()


@app.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return get_project_or_404(db, project_id)


@app.put("/projects/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int, body: schemas.ProjectUpdate, db: Session = Depends(get_db)
):
    project = get_project_or_404(db, project_id)
    project.name = body.name
    project.description = body.description
    db.commit()
    db.refresh(project)
    return project


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    # Relationship cascade also removes this project's requirements and test cases.
    db.delete(project)
    db.commit()
    return {"detail": "Project deleted"}


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------

@app.post("/requirements", response_model=schemas.RequirementOut, status_code=201)
def create_requirement(body: schemas.RequirementCreate, db: Session = Depends(get_db)):
    get_project_or_404(db, body.project_id)
    requirement = models.Requirement(
        project_id=body.project_id,
        title=body.title,
        description=body.description,
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@app.get("/requirements", response_model=list[schemas.RequirementOut])
def list_requirements(project_id: int | None = None, db: Session = Depends(get_db)):
    if project_id is not None:
        get_project_or_404(db, project_id)
    query = select(models.Requirement)
    if project_id is not None:
        query = query.where(models.Requirement.project_id == project_id)
    query = query.order_by(models.Requirement.id)
    return db.scalars(query).all()


@app.get("/requirements/{requirement_id}", response_model=schemas.RequirementOut)
def get_requirement(requirement_id: int, db: Session = Depends(get_db)):
    return get_requirement_or_404(db, requirement_id)


@app.put("/requirements/{requirement_id}", response_model=schemas.RequirementOut)
def update_requirement(
    requirement_id: int,
    body: schemas.RequirementUpdate,
    db: Session = Depends(get_db),
):
    requirement = get_requirement_or_404(db, requirement_id)
    get_project_or_404(db, body.project_id)
    requirement.project_id = body.project_id
    requirement.title = body.title
    requirement.description = body.description
    db.commit()
    db.refresh(requirement)
    return requirement


@app.delete("/requirements/{requirement_id}")
def delete_requirement(requirement_id: int, db: Session = Depends(get_db)):
    requirement = get_requirement_or_404(db, requirement_id)
    # Relationship cascade also removes this requirement's test cases.
    db.delete(requirement)
    db.commit()
    return {"detail": "Requirement deleted"}


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

@app.post("/testcases", response_model=schemas.TestCaseOut, status_code=201)
def create_test_case(body: schemas.TestCaseCreate, db: Session = Depends(get_db)):
    get_requirement_or_404(db, body.requirement_id)
    test_case = models.TestCase(**body.model_dump())
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case


@app.get("/testcases", response_model=list[schemas.TestCaseOut])
def list_test_cases(
    requirement_id: int | None = None,
    project_id: int | None = None,
    type: schemas.TestType | None = None,
    priority: schemas.Priority | None = None,
    status: schemas.Status | None = None,
    db: Session = Depends(get_db),
):
    """List test cases. Every filter is optional and combined with AND."""
    if project_id is not None:
        get_project_or_404(db, project_id)
    if requirement_id is not None:
        get_requirement_or_404(db, requirement_id)

    query = select(models.TestCase).join(models.Requirement)
    if requirement_id is not None:
        query = query.where(models.TestCase.requirement_id == requirement_id)
    if project_id is not None:
        query = query.where(models.Requirement.project_id == project_id)
    if type is not None:
        query = query.where(models.TestCase.type == type)
    if priority is not None:
        query = query.where(models.TestCase.priority == priority)
    if status is not None:
        query = query.where(models.TestCase.status == status)

    query = query.order_by(models.TestCase.id)
    return db.scalars(query).unique().all()


@app.get("/testcases/{test_case_id}", response_model=schemas.TestCaseOut)
def get_test_case(test_case_id: int, db: Session = Depends(get_db)):
    return get_test_case_or_404(db, test_case_id)


@app.put("/testcases/{test_case_id}", response_model=schemas.TestCaseOut)
def update_test_case(
    test_case_id: int, body: schemas.TestCaseUpdate, db: Session = Depends(get_db)
):
    test_case = get_test_case_or_404(db, test_case_id)
    get_requirement_or_404(db, body.requirement_id)
    for field, value in body.model_dump().items():
        setattr(test_case, field, value)
    db.commit()
    db.refresh(test_case)
    return test_case


@app.delete("/testcases/{test_case_id}")
def delete_test_case(test_case_id: int, db: Session = Depends(get_db)):
    test_case = get_test_case_or_404(db, test_case_id)
    db.delete(test_case)
    db.commit()
    return {"detail": "Test case deleted"}


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

EXPORT_COLUMNS = [
    "Requirement",
    "Test Case ID",
    "Title",
    "Type",
    "Preconditions",
    "Steps",
    "Expected Result",
    "Priority",
    "Status",
]


@app.get("/export/{project_id}")
def export_project(project_id: int, db: Session = Depends(get_db)):
    """Download every test case in a project as an .xlsx file."""
    project = get_project_or_404(db, project_id)

    rows = db.execute(
        select(models.Requirement, models.TestCase)
        .join(models.TestCase)
        .where(models.Requirement.project_id == project.id)
        .order_by(models.Requirement.id, models.TestCase.id)
    ).all()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Test Cases"
    sheet.append(EXPORT_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for requirement, test_case in rows:
        sheet.append(
            [
                requirement.title,
                test_case.id,
                test_case.title,
                test_case.type,
                test_case.preconditions or "",
                test_case.steps or "",
                test_case.expected_result or "",
                test_case.priority,
                test_case.status,
            ]
        )

    # Keep the header visible when the sheet is scrolled.
    sheet.freeze_panes = "A2"
    for column, width in zip("ABCDEFGHI", [28, 16, 32, 14, 28, 36, 32, 12, 12]):
        sheet.column_dimensions[column].width = width

    buffer = io.BytesIO()
    workbook.save(buffer)

    filename = f"{safe_filename(project.name)}_test_cases.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Frontend (served by this same app, so the page and API share one origin)
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/style.css")
def styles():
    return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css")


@app.get("/app.js")
def scripts():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="text/javascript")
