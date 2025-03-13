from django.db import models
from users.models import User
from django.utils.timezone import now
from datetime import datetime

# Employee Attendance Model
class EmployeeAttendance(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(default=now)  # One record per day
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ("employee", "date")  # Prevent multiple records per day

    def total_hours(self):
        if self.check_in and self.check_out:
            delta = datetime.combine(self.date, self.check_out) - datetime.combine(self.date, self.check_in)
            return round(delta.total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"{self.employee.username} - {self.date} (Check-in: {self.check_in}, Check-out: {self.check_out})"


# Hospital Service Price List Model
class ServicePrice(models.Model):
    service_name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.service_name} - ${self.price}"

class ManagerMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="manager_sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="manager_received_messages")
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"
