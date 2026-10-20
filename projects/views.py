from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, ProjectForm, RegistrationForm, TaskForm
from .models import Board, Project, ProjectMembership, Task


def home(request):
    return render(request, "projects/home.html")


def health(request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok"})


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account is ready.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    projects = Project.objects.filter(Q(owner=request.user) | Q(members=request.user)).distinct()
    assigned_tasks = Task.objects.filter(assignee=request.user).select_related("board__project")[:8]
    return render(request, "projects/dashboard.html", {"projects": projects, "assigned_tasks": assigned_tasks})


@login_required
def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        ProjectMembership.objects.create(project=project, user=request.user, role=ProjectMembership.Role.OWNER)
        for position, name in enumerate(("To Do", "In Progress", "Done")):
            Board.objects.create(project=project, name=name, position=position)
        messages.success(request, "Project created with a starter board.")
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "title": "Create project", "button_label": "Create project"})


def _member_project(user, pk):
    return get_object_or_404(
        Project.objects.prefetch_related(
            "members",
            Prefetch("boards", queryset=Board.objects.prefetch_related("tasks__assignee")),
        ),
        Q(owner=user) | Q(members=user),
        pk=pk,
    )


@login_required
def project_detail(request, pk):
    project = _member_project(request.user, pk)
    return render(request, "projects/project_detail.html", {"project": project})


@login_required
def task_create(request, project_pk, board_pk):
    project = _member_project(request.user, project_pk)
    board = get_object_or_404(Board, pk=board_pk, project=project)
    form = TaskForm(request.POST or None, project=project)
    form.instance.board = board
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.board = board
        task.created_by = request.user
        task.save()
        messages.success(request, "Task added.")
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "title": f"Add task to {board.name}", "button_label": "Add task"})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task.objects.select_related("board__project", "assignee", "created_by"), pk=pk)
    if not task.board.project.members.filter(pk=request.user.pk).exists() and task.board.project.owner_id != request.user.id:
        return HttpResponseForbidden("You are not a member of this project.")
    form = CommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()
        messages.success(request, "Comment posted.")
        return redirect("task_detail", pk=task.pk)
    return render(request, "projects/task_detail.html", {"task": task, "form": form})
