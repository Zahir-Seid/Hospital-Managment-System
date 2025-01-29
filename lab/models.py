from django.db import models
from users.models import User  

class LabTest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
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
        return f"Test: {self.test_name} | Patient: {self.patient.email} | Status: {self.status}"
