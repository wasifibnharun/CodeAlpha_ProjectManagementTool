import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Activity, Board, Comment, Notification, Project, ProjectMembership, Task


class ProjectFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="StrongPass123!")
        self.member = User.objects.create_user(username="member", email="member@example.com", password="StrongPass123!")
        self.outsider = User.objects.create_user(username="outsider", password="StrongPass123!")
        self.project = Project.objects.create(name="Website launch", description="Ship it", owner=self.owner)
        ProjectMembership.objects.create(project=self.project, user=self.owner, role=ProjectMembership.Role.OWNER)
        ProjectMembership.objects.create(project=self.project, user=self.member)
        self.todo = Board.objects.create(project=self.project, name="To Do", position=0)
        self.done = Board.objects.create(project=self.project, name="Done", position=1)
        self.task = Task.objects.create(
            board=self.todo,
            title="Create wireframe",
            assignee=self.member,
            created_by=self.owner,
            priority=Task.Priority.HIGH,
        )
        self.client.force_login(self.owner)

    def test_project_creation_builds_starter_board_and_activity(self):
        response = self.client.post(reverse("project_create"), {"name": "Mobile launch", "description": "New project"})
        project = Project.objects.get(name="Mobile launch")
        self.assertRedirects(response, reverse("project_detail", args=[project.pk]))
        self.assertEqual(list(project.boards.values_list("name", flat=True)), ["To Do", "In Progress", "Done"])
        self.assertTrue(project.memberships.filter(user=self.owner, role="owner").exists())
        self.assertTrue(project.activities.filter(message="created the project").exists())

    def test_non_member_cannot_open_project_or_task(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse("project_detail", args=[self.project.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("task_detail", args=[self.task.pk])).status_code, 404)

    def test_owner_can_add_member_by_email_and_notification_is_created(self):
        newcomer = User.objects.create_user(username="newcomer", email="new@example.com")
        response = self.client.post(reverse("members_manage", args=[self.project.pk]), {"username_or_email": "new@example.com"})
        self.assertRedirects(response, reverse("members_manage", args=[self.project.pk]))
        self.assertTrue(self.project.members.filter(pk=newcomer.pk).exists())
        self.assertTrue(Notification.objects.filter(recipient=newcomer, project=self.project).exists())
        self.assertTrue(Activity.objects.filter(project=self.project, message__contains="added newcomer").exists())

    def test_regular_member_cannot_manage_team_or_boards(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("members_manage", args=[self.project.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("board_create", args=[self.project.pk]), {"name": "Review"}).status_code, 404)

    def test_member_can_create_task_comment_and_notify_assignee(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("task_create", args=[self.project.pk, self.todo.pk]),
            {"title": "Build page", "description": "", "assignee": self.owner.pk, "priority": "medium", "due_date": ""},
        )
        task = Task.objects.get(title="Build page")
        self.assertRedirects(response, reverse("project_detail", args=[self.project.pk]))
        self.assertTrue(Notification.objects.filter(recipient=self.owner, task=task).exists())
        response = self.client.post(reverse("task_detail", args=[task.pk]), {"body": "Ready for review."})
        self.assertRedirects(response, reverse("task_detail", args=[task.pk]))
        self.assertEqual(task.comments.get().author, self.member)

    def test_assignment_is_limited_to_project_members(self):
        response = self.client.post(
            reverse("task_create", args=[self.project.pk, self.todo.pk]),
            {"title": "Secret", "description": "", "assignee": self.outsider.pk, "priority": "low", "due_date": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(title="Secret").exists())

    def test_member_can_drag_task_to_another_board(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("task_move", args=[self.task.pk]),
            data=json.dumps({"board_id": self.done.pk, "position": 0}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.board, self.done)
        self.assertTrue(Activity.objects.filter(task=self.task, message__contains="moved").exists())

    def test_task_cannot_move_to_board_in_another_project(self):
        other = Project.objects.create(name="Other", owner=self.owner)
        other_board = Board.objects.create(project=other, name="To Do")
        response = self.client.post(
            reverse("task_move", args=[self.task.pk]),
            data=json.dumps({"board_id": other_board.pk, "position": 0}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.task.refresh_from_db()
        self.assertEqual(self.task.board, self.todo)

    def test_only_creator_or_owner_can_delete_task(self):
        member_task = Task.objects.create(board=self.todo, title="Member task", created_by=self.member)
        self.client.force_login(self.member)
        response = self.client.post(reverse("task_delete", args=[self.task.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        response = self.client.post(reverse("task_delete", args=[member_task.pk]))
        self.assertRedirects(response, reverse("project_detail", args=[self.project.pk]))

    def test_nonempty_board_cannot_be_deleted(self):
        response = self.client.post(reverse("board_delete", args=[self.todo.pk]))
        self.assertRedirects(response, reverse("project_detail", args=[self.project.pk]))
        self.assertTrue(Board.objects.filter(pk=self.todo.pk).exists())

    def test_comment_author_and_owner_can_delete_comment(self):
        comment = Comment.objects.create(task=self.task, author=self.member, body="A note")
        response = self.client.post(reverse("comment_delete", args=[comment.pk]))
        self.assertRedirects(response, reverse("task_detail", args=[self.task.pk]))
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

    def test_notification_can_only_be_opened_by_recipient(self):
        notification = Notification.objects.create(recipient=self.member, project=self.project, task=self.task, message="Assigned")
        self.assertEqual(self.client.post(reverse("notification_open", args=[notification.pk])).status_code, 404)
        self.client.force_login(self.member)
        response = self.client.post(reverse("notification_open", args=[notification.pk]))
        self.assertRedirects(response, reverse("task_detail", args=[self.task.pk]))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
