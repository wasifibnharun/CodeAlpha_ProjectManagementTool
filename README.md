# Flowboard - CodeAlpha Project Management Tool

Flowboard is a collaborative project-management application inspired by Trello and Asana. It was built with Django for CodeAlpha Full Stack Development Task 3.

## Features

- Secure registration, login, logout, and route protection
- Group projects with owner and member roles
- Team management by username or email
- Custom project boards and visual task columns
- Task creation, editing, assignment, priority, and due dates
- Drag-and-drop task movement between columns
- Task-level comments and collaboration
- Assignment, comment, and project notifications
- Project activity history
- Permission checks for project, board, task, comment, and notification actions
- Responsive interface for desktop and mobile
- Django admin panel
- PostgreSQL support through `DATABASE_URL`
- Docker, Gunicorn, WhiteNoise, health endpoint, and production security settings

## Technology

- Python 3.13 and Django 6
- HTML, CSS, and vanilla JavaScript
- SQLite for local development
- PostgreSQL for production
- Gunicorn and WhiteNoise
- Docker

## Local setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

To access Django administration:

```powershell
python manage.py createsuperuser
```

Then open `http://127.0.0.1:8000/admin/`.

## Tests

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The suite covers project creation, access isolation, team permissions, task assignment, comments, drag-and-drop movement, guarded deletion, activity records, and notification ownership.

## Environment variables

Copy `.env.example` values into your hosting provider's environment settings. Do not commit real secrets.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Long random production secret |
| `DJANGO_DEBUG` | Set to `false` in production |
| `DATABASE_URL` | PostgreSQL connection string |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins |
| `DJANGO_SECURE_SSL_REDIRECT` | Set to `true` behind HTTPS |
| `DJANGO_SECURE_HSTS_SECONDS` | Start with `3600`, then increase after validation |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | Enable only when every subdomain uses HTTPS |
| `DJANGO_SECURE_HSTS_PRELOAD` | Enable only when the domain is ready for browser preload |

## Render deployment

1. Push this repository to GitHub.
2. Create a Render Web Service from the repository.
3. Select Docker and the free web-service plan.
4. Add `DATABASE_URL` from a PostgreSQL provider. Supabase Session Pooler works with Render's IPv4 network.
5. Add `DJANGO_SECRET_KEY` and set `DJANGO_DEBUG=false`.
6. Set `DJANGO_SECURE_SSL_REDIRECT=true` and `DJANGO_SECURE_HSTS_SECONDS=3600`.
7. Set the health-check path to `/health/`.
8. Deploy. The container applies migrations automatically before Gunicorn starts.

## Main routes

- `/` - landing page
- `/dashboard/` - projects and assigned work
- `/projects/<id>/` - collaborative board
- `/notifications/` - notification inbox
- `/admin/` - Django administration
- `/health/` - deployment health check

## Project structure

```text
config/          Django settings and root URLs
projects/        Models, forms, views, URLs, tests, and migrations
static/          Application CSS and drag-and-drop JavaScript
templates/       Authentication and project-management interfaces
Dockerfile       Production container definition
```

## Submission checklist

- Push the complete source to a repository named `CodeAlpha_ProjectManagementTool`.
- Record a short demonstration covering registration, project creation, team addition, task assignment, drag-and-drop movement, comments, and notifications.
- Include the GitHub repository link in the LinkedIn project post.
- Submit through the CodeAlpha form shared in the internship group.
