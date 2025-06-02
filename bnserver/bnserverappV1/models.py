import datetime
from django.db import models
from django.utils import timezone

class User(models.Model):
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    role = models.CharField(max_length=200)

    def __str__(self):
        return self.username

class UploadedModel(models.Model):
    name = models.CharField(max_length=200, default="Unnamed Network")
    file = models.FileField(upload_to="upload_model/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Questionnaire(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=50)  # e.g., 'text', 'multiple_choice', etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]  # Return first 50 chars of question text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s answer to {self.question.text[:30]}"
