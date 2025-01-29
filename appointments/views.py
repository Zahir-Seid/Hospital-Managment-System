from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import Appointment
from .schemas import AppointmentCreate, AppointmentOut, AppointmentUpdate
from users.views import AuthBearer  # Ensure AuthBearer is correctly defined

# Create a router with authentication
router = Router(tags=["Appointments"], auth=AuthBearer())

# Create an appointment (POST)
@router.post("/create", response={200: AppointmentOut, 400: dict})
def create_appointment(request, payload: AppointmentCreate):
    """
    Create a new appointment (only for patients).
    """
    patient = request.auth  # User authenticated via token

    if patient.role != "patient":
        return 400, {"error": "Only patients can create appointments"}

    # Ensure the doctor exists
    doctor = get_object_or_404(User, id=payload.doctor_id, role='doctor')

    appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=payload.date,
        time=payload.time,
        reason=payload.reason,
    )
    return appointment  # Returns serialized data automatically


# List appointments (GET)
@router.get("/list", response={200: list[AppointmentOut]})
def list_appointments(request):
    """
    List appointments for the logged-in user (patients see their own, doctors see theirs).
    """
    user = request.auth

    if user.role == 'patient':
        appointments = Appointment.objects.filter(patient=user)
    elif user.role == 'doctor':
        appointments = Appointment.objects.filter(doctor=user)
    else:
        return 400, {"error": "Unauthorized"}

    return list(appointments)  # Convert queryset to list for serialization


# Update an appointment (PUT)
@router.put("/update/{appointment_id}", response={200: AppointmentOut, 400: dict})
def update_appointment(request, appointment_id: int, payload: AppointmentUpdate):
    """
    Update an appointment's status or reason (only patient/doctor can update).
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Check if the user is either the doctor or patient of the appointment
    if request.auth != appointment.doctor and request.auth != appointment.patient:
        return 400, {"error": "Unauthorized"}

    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(appointment, attr, value)

    appointment.save()
    return appointment  # Returns the updated appointment


# Delete an appointment (DELETE)
@router.delete("/delete/{appointment_id}", response={200: dict, 400: dict})
def delete_appointment(request, appointment_id: int):
    """
    Delete an appointment (only allowed by the patient or doctor).
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.auth != appointment.doctor and request.auth != appointment.patient:
        return 400, {"error": "Unauthorized"}

    appointment.delete()
    return {"message": "Appointment deleted successfully"}
