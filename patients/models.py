from django.db import models
from users.models import User

class PatientComment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.patient.username} on {self.created_at}"