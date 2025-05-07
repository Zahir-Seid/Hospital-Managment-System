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
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    ssn = models.CharField(max_length=20, unique=True) # for employees can be used for patients as well
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True, 
        default='profile_pictures/default_profile.png'
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

# Patient Profile
class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    region = models.CharField(max_length=50, blank=True, null=True)
    town = models.CharField(max_length=50, blank=True, null=True)
    kebele = models.CharField(max_length=50, blank=True, null=True)
    house_number = models.CharField(max_length=50, blank=True, null=True)
    room_number = models.CharField(max_length=10, blank=True, null=True, unique=True)

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="Doctor_profile")
    department = models.CharField(max_length=50, blank=True, null=True)
    level = models.CharField(max_length=20, blank=True, null=True)