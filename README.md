# CodeAlpha Project Management Tool

Flowboard is a collaborative project-management application built for CodeAlpha Full Stack Development Task 3.

## Phase 1 features

- User registration, login, and logout
- Project creation with a default three-column board
- Project membership model with owner/member roles
- Task creation, priority, due date, and assignment
- Task-level comments
- Responsive dashboard and board interface
- PostgreSQL-ready environment configuration
- Health-check endpoint and production static-file support

## Local setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Test

```powershell
python manage.py test
```

## Planned next phase

Member invitations, board/task editing, drag-and-drop workflow, activity history, and improved permissions.
