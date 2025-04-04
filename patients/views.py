from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import PatientProfile
from appointments.models import Appointment
from lab.models import LabTest
from pharmacy.models import Prescription
from billings.models import Invoice
from .schemas import (
    PatientProfileOut, MedicalHistoryOut, BillingHistoryOut, RoomAssignmentSchema, AppointmentOut, LabTestOut, PrescriptionOut,
    InvoiceOut, PatientCommentCreate, PatientReferralCreate, PatientReferralOut, ChatMessageCreate, ChatMessageOut
)
from users.auth import AuthBearer, AsyncAuthBearer  
from notifications.models import Notification
from notifications.schemas import NotificationOut
from notifications.views import send_notification
from .models import PatientComment, PatientReferral, ChatMessage
from users.models import User, PatientProfile
import pdfkit  
from django.utils.timezone import now
from django.db import models

patients_router = Router(tags=["Patients"])

# Get Patient Profile
@patients_router.get("/profile", response={200: PatientProfileOut}, auth=AuthBearer())
def get_patient_profile(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    profile = get_object_or_404(PatientProfile, user=patient)
    return PatientProfileOut.model_validate(profile).model_dump()  # Updated for Pydantic v2


# Get Medical History
@patients_router.get("/history/medical", response={200: MedicalHistoryOut}, auth=AsyncAuthBearer())
async def get_medical_history(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    appointments = await Appointment.objects.filter(patient=patient).all()
    lab_tests = await LabTest.objects.filter(patient=patient).all()
    prescriptions = await Prescription.objects.filter(patient=patient).all()

    return {
        "appointments": [AppointmentOut.model_validate(a).model_dump() for a in appointments],
        "lab_tests": [LabTestOut.model_validate(l).model_dump() for l in lab_tests],
        "prescriptions": [PrescriptionOut.model_validate(p).model_dump() for p in prescriptions],
    }


# Get Billing History
@patients_router.get("/history/billing", response={200: BillingHistoryOut}, auth=AsyncAuthBearer())
async def get_billing_history(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    invoices = await Invoice.objects.filter(patient=patient).all()
    return {"invoices": [InvoiceOut.model_validate(i).model_dump() for i in invoices]}


# Get Unread Notifications
@patients_router.get("/notifications", response={200: list[NotificationOut]}, auth=AsyncAuthBearer())
async def get_notifications(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    unread_notifications = await Notification.objects.filter(recipient=patient, status="unread").all()
    return [NotificationOut.model_validate(n).model_dump() for n in unread_notifications]


# Mark Notifications as Read
@patients_router.put("/notifications/mark-read", response={200: dict}, auth=AsyncAuthBearer())
async def mark_notifications_read(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    await Notification.objects.filter(recipient=patient, status="unread").update(status="read")
    return {"message": "All notifications marked as read"}


# Download Medical History as PDF
@patients_router.get("/history/download", response={200: dict, 400: dict}, auth=AsyncAuthBearer())
async def download_medical_history(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    appointments = await Appointment.objects.filter(patient=patient).all()
    lab_tests = await LabTest.objects.filter(patient=patient).all()
    prescriptions = await Prescription.objects.filter(patient=patient).all()

    html_content = f"""
    <h2>Medical History for {patient.username}</h2>
    <h3>Appointments:</h3>
    <ul>
    {''.join([f'<li>{a.date} - {a.reason}</li>' for a in appointments])}
    </ul>
    <h3>Lab Tests:</h3>
    <ul>
    {''.join([f'<li>{l.test_name} - {l.status}</li>' for l in lab_tests])}
    </ul>
    <h3>Prescriptions:</h3>
    <ul>
    {''.join([f'<li>{p.medication_name} - {p.status}</li>' for p in prescriptions])}
    </ul>
    """

    pdf_file = f"/tmp/medical_history_{patient.id}.pdf"
    pdfkit.from_string(html_content, pdf_file)

    return {"message": "PDF generated", "file_path": pdf_file}

# Submit a Patient Comment
@patients_router.post("/comment", response={200: dict, 400: dict}, auth=AsyncAuthBearer())
async def submit_comment(request, payload: PatientCommentCreate):
    """
    Patients can submit feedback about the hospital.
    The comment is sent to managers for review.
    """
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Only patients can submit comments"}

    # Save the comment
    comment = await PatientComment.objects.acreate(
        patient=patient,
        message=payload.message
    )

    # Notify all managers (only if managers exist)
    if await User.objects.filter(role="manager").aexists():
        managers = await User.objects.filter(role="manager").all()
        for manager in managers:
            await send_notification(manager, f"New patient comment: {payload.message[:50]}...")  # Limit preview

    return {"message": "Comment submitted successfully"}

# Doctor Refers a Patient
@patients_router.post("/refer", response={200: PatientReferralOut, 400: dict}, auth=AuthBearer())
def refer_patient(request, payload: PatientReferralCreate):
    """
    Doctor refers a patient to another doctor.
    """
    doctor = request.auth

    if doctor.role != "doctor":
        return 400, {"error": "Only doctors can refer patients"}

    patient = get_object_or_404(User, id=payload.patient_id, role="patient")
    referred_doctor = get_object_or_404(User, id=payload.referred_to_id, role="doctor")

    referral = PatientReferral.objects.create(
        doctor=doctor,
        patient=patient,
        referred_to=referred_doctor,
        reason=payload.reason,
        created_at=now(),
    )

    # Notify the referred doctor
    send_notification(referred_doctor, f"You have received a patient referral from Dr. {doctor.username}.")

    return referral

# View Referrals for a Doctor
@patients_router.get("/referrals", response={200: list[PatientReferralOut]}, auth=AuthBearer())
def view_referrals(request):
    """
    Doctors view the referrals they received.
    """
    doctor = request.auth

    if doctor.role != "doctor":
        return 400, {"error": "Only doctors can view referrals"}

    referrals = PatientReferral.objects.filter(referred_to=doctor)
    return referrals

@patients_router.put("/assign-room", response={200: dict, 400: dict}, auth=AuthBearer())
def assign_room(request, payload: RoomAssignmentSchema):
    """
    Assign a room to a patient (Only Record Officers can do this).
    """
    user = request.auth

    if user.role != "record_officer":
        return 400, {"error": "Only record officers can assign rooms"}

    patient_profile = get_object_or_404(PatientProfile, user_id=payload.patient_id)

    # Ensure room number is unique
    if PatientProfile.objects.filter(room_number=payload.room_number).exists():
        return 400, {"error": "Room number already assigned"}

    patient_profile.room_number = payload.room_number
    patient_profile.save()

    return {"message": f"Room {payload.room_number} assigned to patient {patient_profile.user.username}"}

'''
@patients_router.post("/send-message", response={200: ChatMessageOut, 400: dict}, auth=AsyncAuthBearer)
async def send_message(request, payload: ChatMessageCreate):
    """
    Send a chat message via HTTP instead of WebSockets.
    """
    sender = request.auth
    receiver = await User.objects.filter(id=payload.receiver_id).afirst()

    if not receiver:
        return 400, {"error": "Receiver not found"}

    # Save message
    chat_message = await ChatMessage.objects.acreate(
        sender=sender,
        receiver=receiver,
        message=payload.message
    )

    return chat_message
'''

# Get Chat History
@patients_router.get("/chat/history", response={200: list[ChatMessageOut]}, auth=AuthBearer())
def get_chat_history(request, receiver_id: int):
    """
    Fetch chat history between the logged-in user and another user (doctor or patient).
    """
    user = request.auth
    receiver = get_object_or_404(User, id=receiver_id)

    messages = ChatMessage.objects.filter(
        (models.Q(sender=user) & models.Q(receiver=receiver))
        | (models.Q(sender=receiver) & models.Q(receiver=user))
    ).order_by("timestamp")

    return messages

@patients_router.get("/user/patient-records/", response={200: list[PatientProfileOut], 400: dict}, auth=AsyncAuthBearer())
async def get_patient_records(request):
    # Fetch the authenticated user (sender)
    sender = request.auth
    
    # Only allow managers or record officers to fetch patient records
    if sender.role not in ["manager", "record_officer"]:
        return 400, {"error": "Only managers/record_officers can access patient records"}
    
    # Fetch all patients with the role "patient"
    patients = await User.objects.filter(role="patient").all()
    
    # Transform the results into a suitable response format
    patient_list = [
        PatientProfileOut(
            id=patient.id,
            phone_number=patient.phone_number,
            email=patient.email,
            username=patient.username,
            role=patient.role,
            address=patient.address,
            region=patient.region,
            town=patient.town,
            kebele=patient.kebele,
            house_number=patient.house_number,
            room_number=patient.room_number,
            is_active=patient.is_active
        )
        for patient in patients
    ]
    
    return patient_list
