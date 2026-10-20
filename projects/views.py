import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BoardForm, CommentForm, MemberForm, ProjectForm, RegistrationForm, TaskForm
from .models import Activity, Board, Comment, Notification, Project, ProjectMembership, Task


def home(request):
    return render(request, "projects/home.html")


def health(request):
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


def _member_project(user, pk, with_board=False):
    queryset = Project.objects.all()
    if with_board:
        queryset = queryset.prefetch_related(
            "members",
            Prefetch("boards", queryset=Board.objects.prefetch_related("tasks__assignee", "tasks__comments")),
            Prefetch("activities", queryset=Activity.objects.select_related("actor", "task")),
        )
    return get_object_or_404(queryset.filter(Q(owner=user) | Q(members=user)).distinct(), pk=pk)


def _owner_project(user, pk):
    return get_object_or_404(Project, pk=pk, owner=user)


def _member_task(user, pk):
    return get_object_or_404(
        Task.objects.select_related("board__project", "assignee", "created_by").filter(
            Q(board__project__owner=user) | Q(board__project__members=user)
        ).distinct(),
        pk=pk,
    )


def _activity(project, actor, message, task=None):
    return Activity.objects.create(project=project, actor=actor, task=task, message=message)


def _notify(users, project, message, task=None, exclude=None):
    recipient_ids = {user.pk for user in users if user and user.pk != getattr(exclude, "pk", None)}
    Notification.objects.bulk_create(
        [Notification(recipient_id=user_id, project=project, task=task, message=message) for user_id in recipient_ids]
    )


@login_required
def dashboard(request):
    projects = Project.objects.filter(Q(owner=request.user) | Q(members=request.user)).distinct()
    assigned_tasks = Task.objects.filter(assignee=request.user).select_related("board__project")[:8]
    counts = {
        "projects": projects.count(),
        "tasks": Task.objects.filter(assignee=request.user).count(),
        "completed": Task.objects.filter(assignee=request.user, board__name__iexact="Done").count(),
    }
    return render(request, "projects/dashboard.html", {"projects": projects, "assigned_tasks": assigned_tasks, "counts": counts})


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
        _activity(project, request.user, "created the project")
        messages.success(request, "Project created with a starter board.")
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "title": "Create project", "button_label": "Create project"})


@login_required
def project_detail(request, pk):
    project = _member_project(request.user, pk, with_board=True)
    return render(request, "projects/project_detail.html", {"project": project, "is_owner": project.owner_id == request.user.id})


@login_required
def project_update(request, pk):
    project = _owner_project(request.user, pk)
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        _activity(project, request.user, "updated the project details")
        messages.success(request, "Project updated.")
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "title": "Edit project", "button_label": "Save changes"})


@login_required
def project_delete(request, pk):
    project = _owner_project(request.user, pk)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect("dashboard")
    return render(request, "projects/confirm_delete.html", {"object": project, "object_type": "project"})


@login_required
def members_manage(request, pk):
    project = _owner_project(request.user, pk)
    form = MemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        value = form.cleaned_data["username_or_email"].strip()
        user = User.objects.filter(Q(username__iexact=value) | Q(email__iexact=value)).first()
        if not user:
            form.add_error("username_or_email", "No account matches that username or email.")
        elif project.members.filter(pk=user.pk).exists():
            form.add_error("username_or_email", "This person is already a project member.")
        else:
            ProjectMembership.objects.create(project=project, user=user)
            _activity(project, request.user, f"added {user.username} to the project")
            _notify([user], project, f"{request.user.username} added you to {project.name}")
            messages.success(request, f"{user.username} joined the project.")
            return redirect("members_manage", pk=project.pk)
    memberships = project.memberships.select_related("user").order_by("role", "user__username")
    return render(request, "projects/members.html", {"project": project, "memberships": memberships, "form": form})


@require_POST
@login_required
def member_remove(request, project_pk, user_pk):
    project = _owner_project(request.user, project_pk)
    membership = get_object_or_404(ProjectMembership, project=project, user_id=user_pk, role=ProjectMembership.Role.MEMBER)
    username = membership.user.username
    Task.objects.filter(board__project=project, assignee=membership.user).update(assignee=None)
    membership.delete()
    _activity(project, request.user, f"removed {username} from the project")
    messages.success(request, f"{username} was removed.")
    return redirect("members_manage", pk=project.pk)


@login_required
def board_create(request, project_pk):
    project = _owner_project(request.user, project_pk)
    form = BoardForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        board = form.save(commit=False)
        board.project = project
        board.position = project.boards.count()
        board.save()
        _activity(project, request.user, f"created the {board.name} board")
        messages.success(request, "Board created.")
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "title": "Create board", "button_label": "Create board"})


@login_required
def board_update(request, pk):
    board = get_object_or_404(Board.objects.select_related("project"), pk=pk, project__owner=request.user)
    form = BoardForm(request.POST or None, instance=board)
    if request.method == "POST" and form.is_valid():
        form.save()
        _activity(board.project, request.user, f"renamed a board to {board.name}")
        messages.success(request, "Board updated.")
        return redirect("project_detail", pk=board.project_id)
    return render(request, "projects/form.html", {"form": form, "title": "Rename board", "button_label": "Save board"})


@require_POST
@login_required
def board_delete(request, pk):
    board = get_object_or_404(Board.objects.select_related("project"), pk=pk, project__owner=request.user)
    project_id = board.project_id
    if board.tasks.exists():
        messages.error(request, "Move or delete this board's tasks before deleting it.")
    elif board.project.boards.count() == 1:
        messages.error(request, "A project must keep at least one board.")
    else:
        project = board.project
        name = board.name
        board.delete()
        _activity(project, request.user, f"deleted the {name} board")
        messages.success(request, "Board deleted.")
    return redirect("project_detail", pk=project_id)


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
        task.position = board.tasks.count()
        task.save()
        _activity(project, request.user, f"created task: {task.title}", task)
        _notify([task.assignee], project, f"{request.user.username} assigned you: {task.title}", task, request.user)
        messages.success(request, "Task added.")
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "title": f"Add task to {board.name}", "button_label": "Add task"})


@login_required
def task_detail(request, pk):
    task = _member_task(request.user, pk)
    form = CommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()
        _activity(task.board.project, request.user, f"commented on: {task.title}", task)
        _notify([task.assignee, task.created_by], task.board.project, f"{request.user.username} commented on: {task.title}", task, request.user)
        messages.success(request, "Comment posted.")
        return redirect("task_detail", pk=task.pk)
    return render(
        request,
        "projects/task_detail.html",
        {"task": task, "form": form, "can_delete": task.created_by_id == request.user.id or task.board.project.owner_id == request.user.id},
    )


@login_required
def task_update(request, pk):
    task = _member_task(request.user, pk)
    project = task.board.project
    previous_assignee_id = task.assignee_id
    form = TaskForm(request.POST or None, instance=task, project=project)
    if request.method == "POST" and form.is_valid():
        task = form.save()
        _activity(project, request.user, f"updated task: {task.title}", task)
        if task.assignee_id and task.assignee_id != previous_assignee_id:
            _notify([task.assignee], project, f"{request.user.username} assigned you: {task.title}", task, request.user)
        messages.success(request, "Task updated.")
        return redirect("task_detail", pk=task.pk)
    return render(request, "projects/form.html", {"form": form, "title": "Edit task", "button_label": "Save task"})


@require_POST
@login_required
def task_delete(request, pk):
    task = _member_task(request.user, pk)
    if task.created_by_id != request.user.id and task.board.project.owner_id != request.user.id:
        return HttpResponseForbidden("Only the task creator or project owner can delete this task.")
    project = task.board.project
    title = task.title
    task.delete()
    _activity(project, request.user, f"deleted task: {title}")
    messages.success(request, "Task deleted.")
    return redirect("project_detail", pk=project.pk)


@require_POST
@login_required
@transaction.atomic
def task_move(request, pk):
    task = _member_task(request.user, pk)
    try:
        payload = json.loads(request.body or "{}")
        target = Board.objects.get(pk=int(payload["board_id"]), project=task.board.project)
        position = max(0, int(payload.get("position", 0)))
    except (ValueError, TypeError, KeyError, Board.DoesNotExist, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid board or position."}, status=400)
    source = task.board
    task.board = target
    task.save(update_fields=["board", "updated_at"])
    destination_tasks = list(target.tasks.exclude(pk=task.pk).order_by("position", "id"))
    destination_tasks.insert(min(position, len(destination_tasks)), task)
    for index, item in enumerate(destination_tasks):
        if item.position != index:
            Task.objects.filter(pk=item.pk).update(position=index)
    if source.pk != target.pk:
        for index, item in enumerate(source.tasks.order_by("position", "id")):
            if item.position != index:
                Task.objects.filter(pk=item.pk).update(position=index)
    _activity(task.board.project, request.user, f"moved {task.title} to {target.name}", task)
    return JsonResponse({"status": "ok", "board": target.name})


@require_POST
@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("task__board__project"), pk=pk)
    project = comment.task.board.project
    if not project.members.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden("You are not a project member.")
    if comment.author_id != request.user.id and project.owner_id != request.user.id:
        return HttpResponseForbidden("You cannot delete this comment.")
    task_id = comment.task_id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect("task_detail", pk=task_id)


@login_required
def notifications_list(request):
    notifications = request.user.notifications.select_related("project", "task")[:50]
    return render(request, "projects/notifications.html", {"notifications": notifications})


@require_POST
@login_required
def notifications_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications")


@require_POST
@login_required
def notification_open(request, pk):
    notification = get_object_or_404(request.user.notifications, pk=pk)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.task_id:
        return redirect("task_detail", pk=notification.task_id)
    return redirect("project_detail", pk=notification.project_id)
