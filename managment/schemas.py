from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, date, time

# Financial Report Schema
class FinancialReportOut(BaseModel):
    total_revenue: float = Field(..., description="Total revenue generated from approved invoices.")
    pending_payments: float = Field(..., description="Total pending payments.")

# Appointment Report Schema
class AppointmentReportOut(BaseModel):
    total_appointments: int = Field(..., description="Total number of appointments.")

# Service Usage Report Schema
class ServiceUsageOut(BaseModel):
    service_name: str
    count: int

# CSV Export Response Schema
class CSVExportOut(BaseModel):
    csv_file: str = Field(..., description="Base64 encoded CSV file content.")

# Most Used Services Chart Schema
class ChartOut(BaseModel):
    chart: str = Field(..., description="Base64 encoded image of the chart.")

# System Report Schema
class SystemReportOut(BaseModel):
    active_patients: int
    employee_count: int

# Patient Comment Schema
class PatientCommentOut(BaseModel):
    id: int
    patient_id: int
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

# Schema for Marking Attendance (Check-in or Check-out)
class EmployeeAttendanceCreate(BaseModel):
    action: str = Field(..., pattern="^(check_in|check_out)$")
    time: time


# Schema for Viewing Attendance
class EmployeeAttendanceOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    date: date
    check_in: time | None
    check_out: time | None
    total_hours: float | None

    class Config:
        from_attributes = True

# Service Price List Schema
class ServicePriceCreate(BaseModel):
    service_name: str
    price: float

class ServicePriceOut(BaseModel):
    id: int
    service_name: str
    price: float

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    receiver_id: int
    subject: str
    message: str

class MessageOut(BaseModel):
    id: int
    sender: str
    receiver: str
    subject: str
    message: str
    timestamp: datetime
    is_read: bool

    class Config:
        from_attributes = True

class DoctorOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    department: str | None = None
    level: str | None = None
