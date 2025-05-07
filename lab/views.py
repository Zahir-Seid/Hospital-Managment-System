from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import LabTest, StaffMessage
from .schemas import LabTestCreate, LabTestUpdate, LabTestOut, MessageOut
from users.auth import AuthBearer, AsyncAuthBearer
from notifications.utils import send_notification_to_user
from asgiref.sync import sync_to_async
from billings.models import Invoice
lab_router = Router(tags=["Lab Tests"])

# Doctor orders a lab test
@lab_router.post("/order", response={200: LabTestOut, 400: dict}, auth=AsyncAuthBearer())
async def order_lab_test(request, payload: LabTestCreate):
    """
    Doctor orders a lab test for a patient.
    """
    doctor = request.auth

    if doctor.role != "doctor":
        return 400, {"error": "Only doctors can order lab tests"}

    patient = await sync_to_async(get_object_or_404)(User, id=payload.patient_id, role="patient")

    lab_test = await sync_to_async(LabTest.objects.create)(
        doctor=doctor,
        patient=patient,
        test_name=payload.test_name
    )

    # Notify all lab technicians (assuming multiple exist)
    lab_technicians = await sync_to_async(list)(User.objects.filter(role="lab_technician"))
    for technician in lab_technicians:
        await send_notification_to_user(technician, f"New lab test ordered: {payload.test_name} by Dr. {doctor.username}.")

    return {
    "id": lab_test.id,
    "doctor": doctor.username,
    "patient": patient.username,
    "test_name": lab_test.test_name,
    "status": lab_test.status,
    "result": lab_test.result,
    "ordered_at": lab_test.ordered_at,
    "updated_at": lab_test.updated_at
}


# List lab tests (for patient, doctor, or lab technician)
@lab_router.get("/list", response={200: list[dict]}, auth=AuthBearer())
def list_lab_tests(request):
    user = request.auth

    if user.role == "doctor":
        tests = LabTest.objects.filter(doctor=user).select_related('doctor', 'patient')
    elif user.role == "patient":
        tests = LabTest.objects.filter(patient=user).select_related('doctor', 'patient')
    elif user.role == "lab_technician":
        tests = LabTest.objects.select_related('doctor', 'patient').all()
    else:
        return []

    return [
        {
            "id": test.id,
            "test_name": test.test_name,
            "status": test.status,
            "result": test.result,
            "doctor": test.doctor.get_full_name() or test.doctor.username,
            "patient": test.patient.get_full_name() or test.patient.username,
            "ordered_at": test.ordered_at,
            "updated_at": test.updated_at,
        }
        for test in tests
    ]


def send_staff_message(sender: User, receiver_id: int, subject: str, message_body: str):
    receiver = get_object_or_404(User, id=receiver_id)

    message = StaffMessage.objects.create(
        sender=sender,
        receiver=receiver,
        subject=subject,
        message=message_body,
    )
    return message


# Lab Technician updates test status and result
@lab_router.put("/update/{lab_test_id}", response={200: dict, 400: dict}, auth=AuthBearer())
def update_lab_test(request, lab_test_id: int, payload: LabTestUpdate):
    """
    Lab technicians update test results.
    """
    user = request.auth

    if user.role != "lab_technician":
        return 400, {"error": "Only lab technicians can update test results"}

    lab_test = get_object_or_404(LabTest, id=lab_test_id)

    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(lab_test, attr, value)

    lab_test.save()

    # Retrieve all cashiers
    cashiers = User.objects.filter(role="cashier")
    
    # Notify all cashiers
    for cashier in cashiers:
        send_notification_to_user(cashier, f"Lab Test: {lab_test.test_name} for {lab_test.patient} was generated; create an invoice")

    send_notification_to_user(lab_test.doctor, f"Lab result for {lab_test.test_name} is now available. Check out you inbox")
    
    # Send internal message to doctor about the result
    send_staff_message(
        sender=user,
        receiver_id=lab_test.doctor.id,
        subject=f"Lab Result Ready: {lab_test.test_name}",
        message_body=f"The lab result for {lab_test.test_name} is now available.\n\nResult: {lab_test.result or 'Pending'}",
    )
    
    return {
    "id": lab_test.id,
    "test_name": lab_test.test_name,
    "status": lab_test.status,
    "result": lab_test.result,
    "doctor": lab_test.doctor.get_full_name() or lab_test.doctor.username,
    "patient": lab_test.patient.get_full_name() or lab_test.patient.username,
    "ordered_at": lab_test.ordered_at,
    "updated_at": lab_test.updated_at,
}

# Inbox
@lab_router.get("/inbox", response={200: list[MessageOut]}, auth=AuthBearer())
def list_received_messages(request):
    messages = StaffMessage.objects.filter(receiver=request.auth).order_by("-timestamp")
    print(messages)  # Debugging step: Check if any messages are returned
    return [
        {
            "id": message.id,
            "sender": message.sender.username,
            "receiver": message.receiver.username,
            "subject": message.subject,
            "message": message.message,
            "timestamp": message.timestamp,
            "is_read": message.is_read,
        }
        for message in messages
    ]