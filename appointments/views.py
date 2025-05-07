from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import Appointment
from .schemas import AppointmentCreate, AppointmentOut, AppointmentUpdate, SimplePatientResponse
from users.auth import AuthBearer, AsyncAuthBearer
from notifications.views import send_notification
from notifications.utils import send_notification_to_user
from asgiref.sync import sync_to_async

router = Router(tags=["Appointments"])

# Create an appointment
@router.post("/create", response={200: AppointmentOut, 400: dict}, auth=AuthBearer())
def create_appointment(request, payload: AppointmentCreate):
    """
    Create a new appointment (only for patients).
    """
    patient = request.auth

    if patient.role != "patient":
        return 400, {"error": "Only patients can create appointments"}

    doctor = get_object_or_404(User, id=payload.doctor_id, role="doctor")

    # Create the appointment
    appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=payload.date,
        time=payload.time,
        reason=payload.reason,
        status="pending"  # Assuming a default status for new appointments
    )

    # Use the utility function to send the notification
    send_notification_to_user(doctor, f"New appointment request from {patient.username} on {payload.date} at {payload.time}.")

    # Return the response in the format expected by the schema
    return {
        "id": appointment.id,
        "patient": patient.username,  # or patient.id if you prefer the ID
        "doctor": doctor.username,  # or doctor.id if you prefer the ID
        "date": appointment.date,
        "time": appointment.time,
        "status": appointment.status,
        "reason": appointment.reason,
    }


@router.get("/list", response={200: list[AppointmentOut]}, auth=AuthBearer())
def list_appointments(request):
    """
    List appointments for the logged-in user (patients see their own, doctors see theirs).
    """
    user = request.auth

    if user.role == "patient":
        appointments = Appointment.objects.filter(patient=user)
    elif user.role == "doctor":
        appointments = Appointment.objects.filter(doctor=user)
    else:
        return 400, {"error": "Unauthorized"}

    response_data = []

    for a in appointments:
        # Fetch patient and doctor user objects
        patient_user = a.patient
        doctor_user = a.doctor

        # Build profile picture URLs
        patient_profile_pic = request.build_absolute_uri(patient_user.profile_picture.url) if patient_user.profile_picture else None
        # Append formatted appointment data
        response_data.append({
            "id": a.id,
            "patient": str(patient_user), 
            "doctor": str(doctor_user),
            "patient_profile_picture": patient_profile_pic,
            "date": a.date,
            "time": a.time,
            "status": a.status,
            "reason": a.reason,
        })

    return response_data



# Update an appointment
@router.put("/update/{appointment_id}", response={200: AppointmentOut, 400: dict}, auth=AuthBearer())
def update_appointment(request, appointment_id: int, payload: AppointmentUpdate):
    """
    Update an appointment's status or reason (doctor can update).
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.auth != appointment.doctor:
        return 400, {"error": "Unauthorized"}

    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(appointment, attr, value)

    appointment.save()

    notification_recipient = appointment.patient if request.auth == appointment.doctor else appointment.doctor
    send_notification_to_user(notification_recipient, f"Your appointment has been updated to '{appointment.status}'.")

    return {
        "id": appointment.id,
        "patient": appointment.patient.username,
        "doctor": appointment.doctor.username,
        "date": appointment.date,
        "time": appointment.time,
        "status": appointment.status,
        "reason": appointment.reason,
    }



# Delete an appointment
@router.delete("/delete/{appointment_id}", response={200: dict, 400: dict}, auth=AuthBearer())
def delete_appointment(request, appointment_id: int):
    """
    Delete an appointment (only allowed by the patient).
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.auth != appointment.doctor and request.auth != appointment.patient:
        return 400, {"error": "Unauthorized"}

    appointment.delete()

    notification_recipient = appointment.patient if request.auth == appointment.doctor else appointment.doctor
    send_notification_to_user(notification_recipient, f"Your appointment scheduled for {appointment.date} has been canceled.")

    return {"message": "Appointment deleted successfully"}


# Get all patients related to a specific doctor
@router.get("/patients/{doctor_id}", response={200: list[SimplePatientResponse]}, auth=AuthBearer())
def get_patients_of_doctor(request, doctor_id: int):
    # Get the doctor by ID
    doctor = get_object_or_404(User, id=doctor_id, role="doctor")

    # Get all appointments where the doctor is this one and get the patients related to it
    appointments = Appointment.objects.filter(doctor=doctor)

    # Extract the patients from these appointments (ensuring no duplicates)
    patients = {appointment.patient.id: appointment.patient for appointment in appointments}

    # Create response for each patient with only necessary details (id, patient username, doctor username)
    patients_data = []
    for patient in patients.values():
        patients_data.append({
            "id": patient.id,
            "patient": patient.username,
            "doctor": doctor.username,
        })

    return patients_data

# Get all patients who have at least one appointment
@router.get("/patient/list", response={200: list[SimplePatientResponse]}, auth=AuthBearer())
def get_patients_with_appointments(request):
    # Get all appointments in the system
    appointments = Appointment.objects.all()

    # Extract the patients from these appointments (ensuring no duplicates)
    patients = {appointment.patient.id: appointment.patient for appointment in appointments}

    # Create response for each patient with only necessary details (id, patient username)
    patients_data = []
    for patient in patients.values():
        patients_data.append({
            "id": patient.id,
            "patient": patient.username,
        })

    return patients_data