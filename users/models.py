from django.contrib.auth.models import AbstractUser
from django.db import models

# Custom User Model
class User(AbstractUser):
    ROLES = [
        ('manager', 'Manager'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
        ('pharmacist', 'Pharmacist'),
        ('lab_technician', 'Lab Technician'),
        ('cashier', 'Cashier'),
        ('record_officer', 'Record Officer'),
    ]
    role = models.CharField(max_length=20, choices=ROLES, default='patient')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# Base Profile Model for Common Fields
class BaseProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='%(class)s_profile')
    ssn = models.CharField(max_length=20, unique=True)

    class Meta:
        abstract = True


# Role-specific Profiles
class ManagerProfile(BaseProfile):
    pass


class DoctorProfile(BaseProfile):
    department = models.CharField(max_length=50, blank=True, null=True)
    level = models.CharField(max_length=20, blank=True, null=True)


class PharmacistProfile(BaseProfile):
    pass


class LabTechnicianProfile(BaseProfile):
    pass


class CashierProfile(BaseProfile):
    pass


# Patient Profile (Separate as it doesn’t need SSN)
class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    region = models.CharField(max_length=50, blank=True, null=True)
    town = models.CharField(max_length=50, blank=True, null=True)
    kebele = models.CharField(max_length=50, blank=True, null=True)
    house_number = models.CharField(max_length=50, blank=True, null=True)
    room_number = models.CharField(max_length=10, blank=True, null=True, unique=True)

