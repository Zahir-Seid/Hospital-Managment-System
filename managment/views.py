from ninja import Router
from billings.models import Invoice
from appointments.models import Appointment
from lab.models import LabTest
from pharmacy.models import Prescription
from users.models import User, DoctorProfile
from users.schemas import UserOut
from notifications.models import Notification
from notifications.views import send_notification
import matplotlib.pyplot as plt
import io
import base64
import csv
from datetime import datetime, timedelta
from .schemas import (
    FinancialReportOut, AppointmentReportOut, ChartOut, CSVExportOut, SystemReportOut,
    ServiceUsageOut, EmployeeAttendanceCreate, EmployeeAttendanceOut,
    ServicePriceCreate, ServicePriceOut, MessageCreate, MessageOut, PatientCommentOut, DoctorOut
)
from .models import EmployeeAttendance, ServicePrice, ManagerMessage
import pdfkit
from users.auth import AsyncAuthBearer, AuthBearer
from patients.models import PatientComment
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from asgiref.sync import sync_to_async

managment_router = Router(tags=["Managment & Reports"])

# Financial Summary
@managment_router.get("/financial/summary", response={200: FinancialReportOut}, auth=AsyncAuthBearer())
async def financial_summary(request, start_date: str = None, end_date: str = None):
    if request.auth.role not in ["manager", "cashier"]:
        return {"error": "Unauthorized"}

    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    invoices = await sync_to_async(list)(Invoice.objects.filter(created_at__range=[start_date, end_date]))
    total_revenue = sum(i.amount for i in invoices if i.status == "approved")
    pending_payments = sum(i.amount for i in invoices if i.status == "pending")

    return FinancialReportOut(total_revenue=total_revenue, pending_payments=pending_payments)


# Appointments Report
@managment_router.get("/medical/appointments", response={200: AppointmentReportOut}, auth=AsyncAuthBearer())
async def appointments_report(request, doctor_id: int = None):
    if request.auth.role not in ["manager", "doctor"]:
        return {"error": "Unauthorized"}

    filters = {}
    if doctor_id:
        filters["doctor_id"] = doctor_id

    appointments = await sync_to_async(list)(Appointment.objects.filter(**filters))
    return AppointmentReportOut(total_appointments=len(appointments))


# System Overview
@managment_router.get("/system/overview", response={200: SystemReportOut}, auth=AsyncAuthBearer())
async def system_overview(request):
    if request.auth.role != "manager":
        return {"error": "Unauthorized"}

    active_patients = await sync_to_async(User.objects.filter(role="patient").count)()
    employee_count = await sync_to_async(lambda: User.objects.exclude(role__in=["patient", "manager"]).count())()


    return SystemReportOut(
        active_patients=active_patients,
        employee_count=employee_count,
    )

# Most Used Services Chart
@managment_router.get("/system/most-used-services-chart", response={200: ChartOut}, auth=AsyncAuthBearer())
async def most_used_services_chart(request):
    services = {
        "Appointments": await sync_to_async(Appointment.objects.count)(),
        "Lab Tests": await sync_to_async(LabTest.objects.count)(),
        "Prescriptions": await sync_to_async(Prescription.objects.count)(),
    }

    total = sum(services.values())

    if total == 0:
        # show an empty chart or message
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
        ax.axis('off')
    else:
        fig, ax = plt.subplots()
        ax.pie(services.values(), labels=services.keys(), autopct='%1.1f%%')

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return ChartOut(chart=f"data:image/png;base64,{image_base64}")


# Export CSV
@managment_router.get("/export/csv", response={200: CSVExportOut}, auth=AsyncAuthBearer())
async def export_csv(request, report_type: str):
    if request.auth.role != "manager":
        return {"error": "Unauthorized"}

    response = io.StringIO()
    writer = csv.writer(response)

    if report_type == "financial":
        writer.writerow(["Date", "Amount", "Status"])
        invoices = await sync_to_async(list)(Invoice.objects.all())
        for invoice in invoices:
            writer.writerow([invoice.created_at, invoice.amount, invoice.status])

    return CSVExportOut(csv_file=response.getvalue())


# Export PDF
@managment_router.get("/export/pdf", auth=AsyncAuthBearer())
async def export_pdf(request, report_type: str):
    if request.auth.role != "manager":
        return {"error": "Unauthorized"}

    html_content = f"""
    <h1>Hospital Report</h1>
    <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """

    if report_type == "financial":
        invoices = await sync_to_async(list)(Invoice.objects.all())
        html_content += "<h2>Financial Report</h2><table border='1'><tr><th>Date</th><th>Amount</th><th>Status</th></tr>"
        for invoice in invoices:
            html_content += f"<tr><td>{invoice.created_at}</td><td>{invoice.amount}</td><td>{invoice.status}</td></tr>"
        html_content += "</table>"

    pdf_file = f"/tmp/report_{report_type}.pdf"
    pdfkit.from_string(html_content, pdf_file)

    return {"message": "PDF generated", "file_path": pdf_file}

# Patient Comments
@managment_router.get("/patient-comments", response={200: list[PatientCommentOut]}, auth=AsyncAuthBearer())
async def get_patient_comments(request):
    if request.auth.role != "manager":
        return {"error": "Unauthorized"}

    comments = await sync_to_async(list)(PatientComment.objects.all().order_by("-created_at"))
    return [PatientCommentOut.model_validate(c).model_dump() for c in comments]


# Attendance (Sync)
@managment_router.post("/attendance", response={200: EmployeeAttendanceOut, 400: dict}, auth=AuthBearer())
def mark_own_attendance(request, payload: EmployeeAttendanceCreate):
    employee = request.auth

    attendance, created = EmployeeAttendance.objects.get_or_create(employee=employee, date=now().date())

    if payload.action == "check_in":
        if attendance.check_in:
            return 400, {"error": "Check-in already recorded for today"}
        attendance.check_in = payload.time

    elif payload.action == "check_out":
        if not attendance.check_in:
            return 400, {"error": "You must check in before checking out"}
        if attendance.check_out:
            return 400, {"error": "Check-out already recorded for today"}
        attendance.check_out = payload.time

    attendance.save()
    return EmployeeAttendanceOut(
        id=attendance.id,
        employee_id=attendance.employee.id,
        employee_name=attendance.employee.username,
        date=attendance.date,
        check_in=attendance.check_in,
        check_out=attendance.check_out,
        total_hours=attendance.total_hours()
    )


# Attendance List (Sync)
@managment_router.get("/attendance", response={200: list[EmployeeAttendanceOut]}, auth=AuthBearer())
def view_attendance(request):
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can view attendance records"}

    return [
        EmployeeAttendanceOut(
            id=a.id,
            employee_id=a.employee.id,
            employee_name=a.employee.username,
            date=a.date,
            check_in=a.check_in,
            check_out=a.check_out,
            total_hours=a.total_hours()
        )
        for a in EmployeeAttendance.objects.select_related("employee").all()
    ]


# Create Service Price
@managment_router.post("/services", response={200: ServicePriceOut, 400: dict}, auth=AuthBearer())
def add_service_price(request, payload: ServicePriceCreate):
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can manage service prices"}

    service, created = ServicePrice.objects.update_or_create(
        service_name=payload.service_name,
        defaults={"price": payload.price}
    )
    return service


# Read Service Prices
@managment_router.get("/services", response={200: list[ServicePriceOut]})
def view_service_prices(request):
    return ServicePrice.objects.all()


# Update Service Price
@managment_router.put("/services/{service_id}", response={200: ServicePriceOut, 404: dict}, auth=AuthBearer())
def update_service_price(request, service_id: int, payload: ServicePriceCreate):
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can update service prices"}

    try:
        service = ServicePrice.objects.get(id=service_id)
    except ServicePrice.DoesNotExist:
        return 404, {"error": "Service not found"}

    service.service_name = payload.service_name
    service.price = payload.price
    service.save()

    return service


# Delete Service Price
@managment_router.delete("/services/{service_id}", response={200: dict, 404: dict}, auth=AuthBearer())
def delete_service_price(request, service_id: int):
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can delete service prices"}

    try:
        service = ServicePrice.objects.get(id=service_id)
    except ServicePrice.DoesNotExist:
        return 404, {"error": "Service not found"}

    service.delete()
    return {"success": "Service deleted successfully"}



# List Employees
@managment_router.get("/employees/", response={200: list[UserOut], 400: dict}, auth=AuthBearer())
def list_employees(request):
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can view employees"}

    employees = User.objects.exclude(role__in=["manager", "patient"])
    return 200, employees


# Send Message
@managment_router.post("/send", response={200: MessageOut, 400: dict}, auth=AuthBearer())
def send_message(request, payload: MessageCreate):
    sender = request.auth
    if sender.role != "manager":
        return 400, {"error": "Only managers can send messages"}

    receiver = get_object_or_404(User, id=payload.receiver_id)

    # Create the message with the sender and receiver usernames (strings)
    message = ManagerMessage.objects.create(
        sender=sender,  # sender is the actual User instance
        receiver=receiver,  # receiver is the actual User instance
        subject=payload.subject,
        message=payload.message,
    )

    # Return the message using the MessageOut schema
    return {
        "id": message.id,
        "sender": message.sender.username,  
        "receiver": message.receiver.username,
        "subject": message.subject,
        "message": message.message,
        "timestamp": message.timestamp,
        "is_read": message.is_read,
    }

# Inbox
@managment_router.get("/inbox", response={200: list[MessageOut]}, auth=AuthBearer())
def list_received_messages(request):
    messages = ManagerMessage.objects.filter(receiver=request.auth).order_by("-timestamp")
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


# List Doctor Employees
@managment_router.get("/employees/doctors/", response={200: list[DoctorOut], 400: dict}, auth=AuthBearer())
def list_doctor_employees(request):
    if not request.auth:
        print(request)
        return 400, {"error": "Unauthorized"}

    doctors = User.objects.filter(role="doctor")
    doctor_profiles = DoctorProfile.objects.filter(user__in=doctors).select_related("user")

    doctor_data = [
        DoctorOut(
            id=profile.user.id,
            first_name=profile.user.first_name,
            last_name=profile.user.last_name,
            department=profile.department,
            level=profile.level
        )
        for profile in doctor_profiles
    ]

    return 200, doctor_data
