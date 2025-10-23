from django.db import models

class Drawing(models.Model):
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
