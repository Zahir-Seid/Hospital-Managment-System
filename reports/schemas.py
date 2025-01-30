from pydantic import BaseModel, Field
from typing import List

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
    most_used_services: List[ServiceUsageOut]
    unread_notifications: int
