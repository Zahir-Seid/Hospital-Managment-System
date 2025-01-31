from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import PatientProfile
from appointments.models import Appointment
from lab.models import LabTest
from pharmacy.models import Prescription
from billings.models import Invoice
from .schemas import (
    PatientProfileOut, MedicalHistoryOut, BillingHistoryOut, 
    AppointmentOut, LabTestOut, PrescriptionOut, InvoiceOut
)
from users.auth import AuthBearer, AsyncAuthBearer  
from notifications.models import Notification
from notifications.schemas import NotificationOut
from notifications.views import send_notification
from reports.models import PatientComment
from .schemas import PatientCommentCreate
from users.models import User
import pdfkit  

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
    <h2>Medical History for {patient.email}</h2>
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

# ✅ Submit a Patient Comment
@patients_router.post("/comment", response={200: dict, 400: dict}, auth=AsyncAuthBearer())
async def submit_comment(request, payload: PatientCommentCreate):
    """
    Patients can submit feedback about the hospital.
    The comment is sent to the manager for review.
    """
    patient = request.auth
    if patient.role != "patient":
        return 400, {"error": "Only patients can submit comments"}

    # Save the comment in the reports app
    comment = await PatientComment.objects.acreate(
        patient=patient,
        message=payload.message
    )

    # Notify all managers
    managers = await User.objects.filter(role="manager").all()
    for manager in managers:
        await send_notification(manager, "New patient comment received.")

    return {"message": "Comment submitted successfully"}