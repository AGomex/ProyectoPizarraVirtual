from django.db import models

class Drawing(models.Model):
    name = models.CharField(max_length=200, default="Untitled")
    strokes = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    thumbnail = models.ImageField(upload_to="thumbs/", null=True, blank=True)  

    def __str__(self):
        return f"{self.name} ({self.id})"