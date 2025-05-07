from django.db import models
from users.models import User  

class LabTest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lab_tests_as_doctor", limit_choices_to={'role': 'doctor'})
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lab_tests_as_patient", limit_choices_to={'role': 'patient'})
    test_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.TextField(blank=True, null=True)  # Will be updated by Lab Technician
    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Test: {self.test_name} | Patient: {self.patient.username} | Status: {self.status}"


class StaffMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="staff_sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="staff_received_messages")
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"