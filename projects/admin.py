from django.contrib import admin

from .models import Activity, Board, Comment, Notification, Project, ProjectMembership, Task


class MembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "updated_at")
    search_fields = ("name", "description", "owner__username")
    inlines = (MembershipInline,)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "board", "assignee", "priority", "due_date")
    list_filter = ("priority", "board__project")
    search_fields = ("title", "description")


admin.site.register(Board)
admin.site.register(Comment)
admin.site.register(Activity)
admin.site.register(Notification)
