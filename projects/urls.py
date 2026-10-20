from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications_read_all"),
    path("notifications/<int:pk>/open/", views.notification_open, name="notification_open"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/edit/", views.project_update, name="project_update"),
    path("projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path("projects/<int:pk>/members/", views.members_manage, name="members_manage"),
    path("projects/<int:project_pk>/members/<int:user_pk>/remove/", views.member_remove, name="member_remove"),
    path("projects/<int:project_pk>/boards/new/", views.board_create, name="board_create"),
    path("boards/<int:pk>/edit/", views.board_update, name="board_update"),
    path("boards/<int:pk>/delete/", views.board_delete, name="board_delete"),
    path("projects/<int:project_pk>/boards/<int:board_pk>/tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:pk>/", views.task_detail, name="task_detail"),
    path("tasks/<int:pk>/edit/", views.task_update, name="task_update"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/move/", views.task_move, name="task_move"),
    path("comments/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
]
