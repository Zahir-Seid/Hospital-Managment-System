from django.db import models
from users.models import User
from django.utils.timezone import now

class PatientComment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.patient.username} on {self.created_at}"

# Patient Referral Model
class PatientReferral(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referring_doctor")
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referred_patient")
    referred_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referred_doctor")
    reason = models.TextField()
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"Referral: {self.patient.username} -> {self.referred_to.username} ({self.created_at})"

# Chat Message Model
class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} at {self.timestamp}"