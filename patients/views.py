from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import PatientProfile
from appointments.models import Appointment
from lab.models import LabTest
from pharmacy.models import Prescription
from billings.models import Invoice
from .schemas import (
    PatientProfileOut, MedicalHistoryOut, BillingHistoryOut, RoomAssignmentSchema, AppointmentOut, LabTestOut, PrescriptionOut,
    InvoiceOut, PatientCommentCreate, PatientReferralCreate, PatientReferralOut, ChatMessageCreate,  UserOut
)
from users.auth import AuthBearer, AsyncAuthBearer  
from notifications.models import Notification
from notifications.schemas import NotificationOut
from notifications.views import send_notification
from notifications.utils import send_notification_to_user
from .models import PatientComment, PatientReferral, ChatMessage
from users.models import User, PatientProfile
import pdfkit  
from django.utils.timezone import now
from django.db import models
from asgiref.sync import sync_to_async

patients_router = Router(tags=["Patients"])
async_send_notification = sync_to_async(send_notification)

# Get Patient Profile
@patients_router.get("/profile", response={200: dict}, auth=AuthBearer())
def get_patient_profile(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    profile = get_object_or_404(PatientProfile, user=patient)

    # Manually convert model to dict
    data = PatientProfileOut.model_validate(profile).model_dump()

    # Build full URL for profile picture
    if patient.profile_picture:
        data["user"]["profile_picture"] = request.build_absolute_uri(patient.profile_picture.url)
    else:
        data["user"]["profile_picture"] = None

    return 200, data


# Get Medical History
@patients_router.get("/history/medical", response={200: MedicalHistoryOut}, auth=AuthBearer())
def get_medical_history(request):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Unauthorized"}

    appointments = Appointment.objects.filter(patient=patient).all()
    lab_tests = LabTest.objects.filter(patient=patient).all()
    prescriptions =  Prescription.objects.filter(patient=patient).all()

    return {
        "appointments": [
            AppointmentOut.model_validate({
                **a.__dict__,  # Convert the Appointment object to a dict
                "doctor": a.doctor.username,  # Assuming you want the doctor's username
                "time": a.time.strftime("%H:%M"),  # Convert time to string in the format HH:MM
            }).model_dump() for a in appointments
        ],
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

    await Notification.objects.filter(recipient=patient, status="unread").aupdate(status="read")
    return {"message": "All notifications marked as read"}

# Submit a Patient Comment
@patients_router.post("/comment", response={200: dict, 400: dict}, auth=AuthBearer())
def submit_comment(request, payload: PatientCommentCreate):
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Only patients can submit comments"}

    comment = PatientComment.objects.acreate(
        patient=patient,
        message=payload.message
    )

    if User.objects.filter(role="manager").aexists():
        managers = User.objects.filter(role="manager").all()
        for manager in managers:
            async_send_notification(manager, f"New patient comment: {payload.message[:50]}...")

    return {"message": "Comment submitted successfully"}


# Doctor Refers a Patient
@patients_router.post("/refer", response={200: dict, 400: dict}, auth=AuthBearer())
def refer_patient(request, payload: PatientReferralCreate):
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

    send_notification_to_user(referred_doctor, f"You have received a patient referral from Dr. {doctor.username}.")

    return {
        "id": referral.id,
        "doctor": str(referral.doctor),           
        "patient": str(referral.patient),         
        "referred_to": str(referral.referred_to), 
        "reason": referral.reason,
        "created_at": referral.created_at,
    }



# View Referrals for a Doctor
@patients_router.get("/referrals", response={200: list[PatientReferralOut]}, auth=AuthBearer())
def view_referrals(request):
    doctor = request.auth

    if doctor.role != "doctor":
        return 400, {"error": "Only doctors can view referrals"}

    referrals = PatientReferral.objects.filter(referred_to=doctor)
    return referrals


@patients_router.put("/assign-room", response={200: dict, 400: dict}, auth=AuthBearer())
def assign_room(request, payload: RoomAssignmentSchema):
    user = request.auth

    if user.role != "record_officer":
        return 400, {"error": "Only record officers can assign rooms"}

    patient_profile = get_object_or_404(PatientProfile, user_id=payload.patient_id)

    if PatientProfile.objects.filter(room_number=payload.room_number).exists():
        return 400, {"error": "Room number already assigned"}

    patient_profile.room_number = payload.room_number
    patient_profile.save()

    return {"message": f"Room {payload.room_number} assigned to patient {patient_profile.user.username}"}


# Get Chat History
@patients_router.get("/chat/history", response={200: list[dict]}, auth=AuthBearer())
def get_chat_history(request, receiver_id: int):
    user = request.auth
    if user.role not in ['patient', 'doctor']:
        return 401, {"message": "Unauthorized"}

    receiver = get_object_or_404(User, id=receiver_id)

    messages = ChatMessage.objects.filter(
        (models.Q(sender=user) & models.Q(receiver=receiver)) |
        (models.Q(sender=receiver) & models.Q(receiver=user))
    ).order_by("timestamp")

    serialized_messages = [
        {
            "id": msg.id,
            "sender": msg.sender.username,  
            "receiver": msg.receiver.username,  
            "message": msg.message,
            "timestamp": msg.timestamp,
        }
        for msg in messages
    ]

    return serialized_messages



@patients_router.get("/user/patient-records/", response={200: list[PatientProfileOut], 400: dict}, auth=AuthBearer())
def get_patient_records(request):
    sender = request.auth

    if sender.role not in ["manager", "record_officer"]:
        return 400, {"error": "Only managers/record_officers can access patient records"}

    # Fetch all patients with their related PatientProfile
    patients = User.objects.filter(role="patient", patient_profile__isnull=False).select_related("patient_profile")

    patient_list = [
        PatientProfileOut(
            user=UserOut.from_orm(patient),
            region=patient.patient_profile.region or "",
            town=patient.patient_profile.town or "",
            kebele=patient.patient_profile.kebele or "",
            house_number=patient.patient_profile.house_number or "",
            room_number=patient.patient_profile.room_number
        )
        for patient in patients
    ]

    return patient_list


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