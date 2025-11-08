from django.db import models
from django.contrib.auth.models import User 

class Drawing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="drawings", null=True, blank=True)
    name = models.CharField(max_length=200, default="Untitled")
    strokes = models.JSONField(default=list)
    width = models.IntegerField(default=640)
    height = models.IntegerField(default=480)
    background_color = models.CharField(max_length=20, default="#FFFFFF")
    thumbnail = models.ImageField(upload_to="thumbs/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.id})"
