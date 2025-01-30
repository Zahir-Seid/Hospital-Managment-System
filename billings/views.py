from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import Invoice
from .schemas import InvoiceCreate, InvoiceUpdate, InvoiceOut
from users.views import AuthBearer  
from notifications.views import send_notification  
import requests
import os
import uuid

billings_router = Router(tags=["Billing"], auth=AuthBearer())

CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
CHAPA_INIT_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify"

# Create an invoice
@billings_router.post("/create", response={200: InvoiceOut, 400: dict})
async def create_invoice(request, payload: InvoiceCreate):
    # Generate a new invoice for a patient.
    user = request.auth

    if user.role != "cashier":
        return 400, {"error": "Only cashiers can create invoices"}
    
    patient = get_object_or_404(User, id=payload.patient_id, role="patient")

    invoice = Invoice.objects.create(
        patient=patient,
        amount=payload.amount,
        description=payload.description
    )
    
    # Notify the patient about the new invoice
    await send_notification(patient, f"A new invoice of ${payload.amount} has been generated for you.")

    return invoice


# Generate Chapa Payment Link
@billings_router.post("/pay/{invoice_id}", response={200: dict, 400: dict})
async def generate_chapa_payment_link(request, invoice_id: int, phone_number: str):
    invoice = get_object_or_404(Invoice.objects.select_related("patient"), id=invoice_id, status="pending")
    tx_ref = f"invoice_{invoice.id}_{uuid.uuid4().hex[:8]}"
    invoice.tx_ref = tx_ref
    invoice.save()
    
    payload = {
        "amount": str(invoice.amount),
        "currency": "ETB",
        "email": invoice.patient.email,
        "first_name": invoice.patient.first_name,
        "last_name": invoice.patient.last_name,
        "phone_number": phone_number,
        "tx_ref": tx_ref,
        "callback_url": f"http://localhost:8000/api/billing/verify/{invoice.id}",
        "return_url": f"http://localhost:8000/payment-success",
        "customization": {
            "title": "Hospital Payment",
            "description": invoice.description,
        },
    }
    
    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}", "Content-Type": "application/json"}
    response = requests.post(CHAPA_INIT_URL, json=payload, headers=headers)
    data = response.json()
    
    if response.status_code == 200 and "data" in data:
        invoice.chapa_payment_url = data["data"]["checkout_url"]
        invoice.save()
        return {"payment_url": invoice.chapa_payment_url}
    else:
        return 400, {"error": "Failed to generate payment link."}


# List invoices for a patient
@billings_router.get("/list", response={200: list[InvoiceOut]})
def list_invoices(request):
    #Retrieve invoices for the logged-in patient.
    user = request.auth

    if user.role != "patient":
        return 400, {"error": "Only patients can view their invoices"}
    
    return Invoice.objects.filter(patient=user)

# Confirm Chapa Payment
@billings_router.post("/verify/{invoice_id}", response={200: dict, 400: dict})
async def confirm_payment(request, invoice_id: int):
    invoice = get_object_or_404(Invoice.objects.select_related("patient"), id=invoice_id, status="pending")
    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}", "Content-Type": "application/json"}
    response = requests.get(f"{CHAPA_VERIFY_URL}/{invoice.tx_ref}", headers=headers)
    data = response.json()
    
    if response.status_code == 200 and data.get("status") == "success":
        invoice.status = "paid"
        invoice.save()
        cashiers = await User.objects.filter(role="cashier").all()
        for cashier in cashiers:
            await send_notification(cashier, f"Payment received for invoice #{invoice.id}. Please review and approve.")

        return {"message": "Payment verified. Awaiting approval."}
    
    return 400, {"error": "Payment verification failed."}


# Cashier approves a payment
@billings_router.put("/approve/{invoice_id}", response={200: InvoiceOut, 400: dict})
async def approve_payment(request, invoice_id: int, payload: InvoiceUpdate):
    # Cashier manually approves a payment after confirmation.
    user = request.auth

    if user.role != "cashier":
        return 400, {"error": "Only cashiers can approve payments"}
    
    invoice = get_object_or_404(Invoice, id=invoice_id, status="paid")

    invoice.status = "approved"
    invoice.save()

    # Notify the patient that their payment is approved
    await send_notification(invoice.patient, f"Your payment of ${invoice.amount} has been approved.")

    return invoice
