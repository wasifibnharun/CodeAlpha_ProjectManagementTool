from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Board, Project, ProjectMembership, Task


class ProjectFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="StrongPass123!")
        self.client.login(username="owner", password="StrongPass123!")

    def test_project_creation_builds_starter_board(self):
        response = self.client.post(reverse("project_create"), {"name": "Website launch", "description": "Ship it"})
        project = Project.objects.get(name="Website launch")
        self.assertRedirects(response, reverse("project_detail", args=[project.pk]))
        self.assertEqual(list(project.boards.values_list("name", flat=True)), ["To Do", "In Progress", "Done"])
        self.assertTrue(ProjectMembership.objects.filter(project=project, user=self.user, role="owner").exists())

    def test_non_member_cannot_open_project(self):
        project = Project.objects.create(name="Private", owner=User.objects.create_user("other"))
        response = self.client.get(reverse("project_detail", args=[project.pk]))
        self.assertEqual(response.status_code, 404)

    def test_member_can_create_task_and_comment(self):
        project = Project.objects.create(name="Build", owner=self.user)
        ProjectMembership.objects.create(project=project, user=self.user, role="owner")
        board = Board.objects.create(project=project, name="To Do")
        response = self.client.post(
            reverse("task_create", args=[project.pk, board.pk]),
            {"title": "Create wireframe", "description": "", "assignee": self.user.pk, "priority": "high", "due_date": ""},
        )
        task = Task.objects.get(title="Create wireframe")
        self.assertRedirects(response, reverse("project_detail", args=[project.pk]))
        response = self.client.post(reverse("task_detail", args=[task.pk]), {"body": "Started working on this."})
        self.assertRedirects(response, reverse("task_detail", args=[task.pk]))
        self.assertEqual(task.comments.get().author, self.user)
