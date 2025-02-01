from django.db import models
from users.models import User
from django.utils.timezone import now

# Employee Attendance Model
class EmployeeAttendance(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(default=now)  # Ensure one record per day
    status = models.CharField(max_length=10, choices=[("present", "Present"), ("absent", "Absent")], default="present")

    class Meta:
        unique_together = ("employee", "date")  # Prevent multiple records for the same employee per day

    def __str__(self):
        return f"{self.employee.username} - {self.date} ({self.status})"


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
