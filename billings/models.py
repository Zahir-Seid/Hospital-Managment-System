from django.db import models
from users.models import User

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('approved', 'Approved'),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices", limit_choices_to={'role': 'patient'})
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    chapa_payment_url = models.URLField(blank=True, null=True)  # Chapa payment link
    tx_ref = models.CharField(max_length=100, unique=True, blank=True, null=True)  # Unique transaction reference
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.patient.email} - {self.status}"
