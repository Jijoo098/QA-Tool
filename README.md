# QA Test Case Manager

Phase 1 of a QA tool. Testers can store projects, requirements, and test cases, then export a project to Excel. There are no AI features in this phase.

## Setup

From this folder (`qa-tool`):

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r backend\requirements.txt
```

The database file path is in `.env`:

```
DATABASE_URL=sqlite:///./qa.db
```

If that line is missing, the app still creates `qa.db` in this folder.

## Run

With the virtual environment active, from this same folder:

```powershell
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000

- The page is served at `/`
- API docs are at http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## How to use the page

1. Add a project in the left sidebar.
2. Select it, then add a requirement.
3. Select the requirement and add test cases.
4. Filter the table by type, priority, or status.
5. Use **Export to Excel** to download that project's test cases.

Deleting a project also deletes its requirements and test cases. Deleting a requirement also deletes its test cases.
