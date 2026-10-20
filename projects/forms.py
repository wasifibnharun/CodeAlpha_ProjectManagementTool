from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Comment, Project, Task


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "description", "assignee", "priority", "due_date")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = project.members.all() if project else User.objects.none()


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "placeholder": "Write a comment..."})}
