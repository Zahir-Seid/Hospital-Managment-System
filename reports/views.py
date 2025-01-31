from ninja import Router
from billings.models import Invoice
from appointments.models import Appointment
from lab.models import LabTest
from pharmacy.models import Prescription
from users.models import User
from notifications.models import Notification
from notifications.views import send_notification
import matplotlib.pyplot as plt
import io
import base64
import csv
from datetime import datetime, timedelta
from .schemas import FinancialReportOut, AppointmentReportOut, ChartOut, CSVExportOut, SystemReportOut, ServiceUsageOut, EmployeeAttendanceCreate, EmployeeAttendanceOut, ServicePriceCreate, ServicePriceOut
from .models import EmployeeAttendance, ServicePrice
import pdfkit
from users.auth import AsyncAuthBearer, AuthBearer
from patients.models import PatientComment
from .schemas import PatientCommentOut
from django.utils.timezone import now

reports_router = Router(tags=["Reports"])

# Generate Financial Report
@reports_router.get("/financial/summary", response={200: FinancialReportOut}, auth=AsyncAuthBearer())
async def financial_summary(request, start_date: str = None, end_date: str = None):
    """
    Fetch financial summary: total revenue, pending vs. approved payments.
    """
    if not request.auth.role in ["admin", "cashier"]:
        return {"error": "Unauthorized"}
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    invoices = await Invoice.objects.filter(created_at__range=[start_date, end_date]).all()
    total_revenue = sum(i.amount for i in invoices if i.status == "approved")
    pending_payments = sum(i.amount for i in invoices if i.status == "pending")
    
    return FinancialReportOut(total_revenue=total_revenue, pending_payments=pending_payments)

# Generate Appointments Report
@reports_router.get("/medical/appointments", response={200: AppointmentReportOut}, auth=AsyncAuthBearer())
async def appointments_report(request, doctor_id: int = None):
    """
    Get total appointments per doctor.
    """
    if request.auth.role not in ["admin", "doctor"]:
        return {"error": "Unauthorized"}
    
    filters = {}
    if doctor_id:
        filters["doctor_id"] = doctor_id
    
    appointments = await Appointment.objects.filter(**filters).all()
    total_appointments = len(appointments)
    return AppointmentReportOut(total_appointments=total_appointments)

# Generate System-Wide Report
@reports_router.get("/system/overview", response={200: SystemReportOut}, auth=AsyncAuthBearer())
async def system_overview(request):
    """
    Fetch system-wide statistics: active patients, unread notifications.
    """
    if request.auth.role != "admin":
        return {"error": "Unauthorized"}
    
    active_patients = await User.objects.filter(role="patient").count()
    unread_notifications = await Notification.objects.filter(status="unread").count()

    return SystemReportOut(
        active_patients=active_patients,
        unread_notifications=unread_notifications,
        most_used_services=[]
    )

# Generate Most Used Services Report
@reports_router.get("/system/most-used-services", response={200: list[ServiceUsageOut]}, auth=AsyncAuthBearer())
async def most_used_services(request):
    """
    Fetch most used services in the hospital.
    """
    if request.auth.role != "admin":
        return {"error": "Unauthorized"}

    services = [
        ServiceUsageOut(service_name="Appointments", count=await Appointment.objects.count()),
        ServiceUsageOut(service_name="Lab Tests", count=await LabTest.objects.count()),
        ServiceUsageOut(service_name="Prescriptions", count=await Prescription.objects.count()),
    ]
    
    return services

# Generate Chart for Most Used Services
@reports_router.get("/system/most-used-services-chart", response={200: ChartOut}, auth=AsyncAuthBearer())
async def most_used_services_chart(request):
    """
    Generate a pie chart for most used services.
    """
    services = {
        "Appointments": await Appointment.objects.count(),
        "Lab Tests": await LabTest.objects.count(),
        "Prescriptions": await Prescription.objects.count(),
    }
    
    fig, ax = plt.subplots()
    ax.pie(services.values(), labels=services.keys(), autopct='%1.1f%%')
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    
    return ChartOut(chart=f"data:image/png;base64,{image_base64}")

# Export Report as CSV
@reports_router.get("/export/csv", response={200: CSVExportOut}, auth=AsyncAuthBearer())
async def export_csv(request, report_type: str):
    """
    Export financial or medical reports as CSV.
    """
    if request.auth.role != "admin":
        return {"error": "Unauthorized"}
    
    response = io.StringIO()
    writer = csv.writer(response)
    
    if report_type == "financial":
        writer.writerow(["Date", "Amount", "Status"])
        invoices = await Invoice.objects.all()
        for invoice in invoices:
            writer.writerow([invoice.created_at, invoice.amount, invoice.status])
    
    csv_data = response.getvalue()
    return CSVExportOut(csv_file=csv_data)

# Export Report as PDF
@reports_router.get("/export/pdf", auth=AsyncAuthBearer())
async def export_pdf(request, report_type: str):
    """
    Export financial or medical reports as PDF.
    """
    if request.auth.role != "admin":
        return {"error": "Unauthorized"}
    
    html_content = """
    <h1>Hospital Report</h1>
    <p>Generated on: {}</p>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    if report_type == "financial":
        invoices = await Invoice.objects.all()
        html_content += "<h2>Financial Report</h2><table border='1'><tr><th>Date</th><th>Amount</th><th>Status</th></tr>"
        for invoice in invoices:
            html_content += f"<tr><td>{invoice.created_at}</td><td>{invoice.amount}</td><td>{invoice.status}</td></tr>"
        html_content += "</table>"
    
    pdf_file = f"/tmp/report_{report_type}.pdf"
    pdfkit.from_string(html_content, pdf_file)
    
    return {"message": "PDF generated", "file_path": pdf_file}

# Notify Admin When Reports Are Generated
async def notify_admin(report_name):
    admin_users = await User.objects.filter(role="admin").all()
    for admin in admin_users:
        await send_notification(admin, f"{report_name} report has been generated.")


# Get Patient Comments (Managers Only)
@reports_router.get("/patient-comments", response={200: list[PatientCommentOut]}, auth=AsyncAuthBearer())
async def get_patient_comments(request):
    """
    Retrieve all patient comments (only for managers).
    """
    if request.auth.role != "manager":
        return {"error": "Unauthorized"}

    comments = await PatientComment.objects.all().order_by("-created_at")
    return [PatientCommentOut.model_validate(c).model_dump() for c in comments]

# Employees Mark Their Own Attendance
@reports_router.post("/attendance", response={200: EmployeeAttendanceOut, 400: dict}, auth=AuthBearer())
def mark_own_attendance(request, payload: EmployeeAttendanceCreate):
    """
    Employees mark their own attendance. Each employee can only mark once per day.
    """
    employee = request.auth  # Get authenticated user

    # Prevent duplicate attendance entry for the same day
    if EmployeeAttendance.objects.filter(employee=employee, date=now().date()).exists():
        return 400, {"error": "Attendance already marked for today"}

    attendance = EmployeeAttendance.objects.create(employee=employee, status=payload.status)
    return attendance

# Managers View All Employee Attendance Records
@reports_router.get("/attendance", response={200: list[EmployeeAttendanceOut]}, auth=AuthBearer())
def view_attendance(request):
    """
    Managers view all employee attendance records.
    """
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can view attendance records"}

    return [
        EmployeeAttendanceOut(
            id=a.id, employee_id=a.employee.id, employee_name=a.employee.username, date=a.date, status=a.status
        ) for a in EmployeeAttendance.objects.all()
    ]

# Add/Update Hospital Service Prices
@reports_router.post("/services", response={200: ServicePriceOut, 400: dict}, auth=AuthBearer)
def add_service_price(request, payload: ServicePriceCreate):
    """
    Manager adds or updates the price of a hospital service.
    """
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can manage service prices"}

    service, created = ServicePrice.objects.update_or_create(
        service_name=payload.service_name,
        defaults={"price": payload.price}
    )
    return service

# View Hospital Service Prices
@reports_router.get("/services", response={200: list[ServicePriceOut]})
def view_service_prices(request):
    """
    View all hospital service prices.
    """
    return ServicePrice.objects.all()