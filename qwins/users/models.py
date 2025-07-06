from django.db import models
from django.utils import timezone


class BillTokenSession(models.Model):
    username = models.CharField(max_length=255, unique=True)
    session_token = models.CharField(max_length=255, unique=True)
    bill_token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()


class UserProfile(models.Model):
    username = models.CharField(max_length=255, unique=True)
    tickets = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.username}: {self.tickets} tickets"


class Task(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=255)
    reward = models.PositiveIntegerField(default=1)
    text = models.TextField()
    svg = models.TextField()
    action_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title


class SolvedTask(models.Model):
    username = models.CharField(max_length=255)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("username", "task")


class Promocode(models.Model):
    username = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True)
    prize = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.prize


class Prize(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    drop_chance = models.FloatField()  # шанс выпадения, например 5.0 означает 5%

    def __str__(self):
        return self.name
