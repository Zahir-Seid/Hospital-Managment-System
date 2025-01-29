from django.db import models
from users.models import User  

class Drug(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)  # Track available stock
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.stock_quantity} in stock"

class Prescription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('dispensed', 'Dispensed'),
    ]

    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescriptions_as_doctor", limit_choices_to={'role': 'doctor'})
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescriptions_as_patient", limit_choices_to={'role': 'patient'})
    medication_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=100)
    instructions = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    prescribed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prescription: {self.medication_name} for {self.patient.email} | Status: {self.status}"
