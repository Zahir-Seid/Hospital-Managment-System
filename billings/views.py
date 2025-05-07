from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import Invoice
from .schemas import InvoiceCreate, InvoiceOut, InvoiceUpdate
from users.auth import AuthBearer, AsyncAuthBearer
from notifications.utils import send_notification_to_user
from notifications.views import send_notification
import requests
import os
import uuid
from asgiref.sync import sync_to_async
import hmac
import hashlib
import json
import httpx
from django.http import JsonResponse, HttpRequest
from ninja.errors import HttpError
from dotenv import load_dotenv
load_dotenv()
from decimal import Decimal

billings_router = Router(tags=["Billing"])




CHAPA_WEBHOOK_SECRET = os.getenv("CHAPA_WEBHOOK_SECRET")
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
CHAPA_INIT_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify"

# Create an invoice
@billings_router.post("/create", response={200: dict, 400: dict}, auth=AuthBearer())
def create_invoice(request, payload: InvoiceCreate):
    user = request.auth

    if user.role != "cashier":
        return 400, {"error": "Only cashiers can create invoices"}
    
    patient = get_object_or_404(User, id=payload.patient_id, role="patient")

    invoice = Invoice.objects.create(
        patient=patient,
        amount=payload.amount,
        description=payload.description
    )
    print(patient)
    send_notification_to_user(patient, f"A new invoice of ${payload.amount} has been generated for you.")

    response_data = {
        "id": invoice.id,
        "patient": patient.username,
        "amount": invoice.amount,
        "description": invoice.description,
        "status": invoice.status,
        "chapa_payment_url": invoice.chapa_payment_url,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
    }

    return response_data


# Generate Chapa Payment Link
@billings_router.post("/pay/{invoice_id}", response={200: dict, 400: dict}, auth=AsyncAuthBearer())
async def generate_chapa_payment_link(request, invoice_id: int):
    invoice = await sync_to_async(get_object_or_404)(
        Invoice.objects.select_related("patient"),
        id=invoice_id,
        status="pending"
    )

    tx_ref = f"invoice_{invoice.id}_{uuid.uuid4().hex[:8]}"
    invoice.tx_ref = tx_ref
    await sync_to_async(invoice.save)()

    payload = {
        "amount": str(invoice.amount),
        "currency": "ETB",
        "email": invoice.patient.email,
        "first_name": invoice.patient.first_name,
        "last_name": invoice.patient.last_name,
        "tx_ref": tx_ref,
        "callback_url": f"http://localhost:8000/api/billing/callback/",
        "return_url": f"http://localhost:3000/payment-success",
        "customization": {
            "title": "Hospital Payment",
            "description": invoice.description,
        },
    }

    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}", "Content-Type": "application/json"}
    response = requests.post(CHAPA_INIT_URL, json=payload, headers=headers)
    data = response.json()
    print(data)
    if response.status_code == 200 and "data" in data:
        invoice.chapa_payment_url = data["data"]["checkout_url"]
        await sync_to_async(invoice.save)()
        return {"payment_url": invoice.chapa_payment_url}
    else:
        return 400, {"error": "Failed to generate payment link."}


@billings_router.get("/list", response={200: list[InvoiceOut]}, auth=AuthBearer())
def list_invoices(request):
    user = request.auth

    if user.role != "patient":
        raise HttpError(400, "Only patients can view their invoices")

    invoices = Invoice.objects.filter(patient=user)

    # Manually serialize to match InvoiceOut expectations
    results = [
        {
            "id": invoice.id,
            "patient": invoice.patient.username,  # Convert User to string
            "amount": invoice.amount,
            "description": invoice.description,
            "status": invoice.status,
            "chapa_payment_url": invoice.chapa_payment_url,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
        }
        for invoice in invoices
    ]

    return results

@billings_router.get("/logs", response={200: list[dict]}, auth=AuthBearer())
def list_all_invoices_for_cashier(request):
    user = request.auth

    if user.role != "cashier":
        return {"error": "Only cashiers can view invoice logs"}

    invoices = Invoice.objects.select_related("patient").all()

    # Serialize the invoices
    returned_invoices = [
        {
            "id": invoice.id,
            "description": invoice.description,
            "amount": str(invoice.amount),
            "status": invoice.status,
            "patient_username": invoice.patient.username,  
            "created_at": invoice.created_at.isoformat(),  
        }
        for invoice in invoices
    ]
    print(returned_invoices)
    return returned_invoices

# chapa payment verification 
@billings_router.post("/callback")
async def chapa_webhook(request: HttpRequest):
    # Raw body for signature verification
    body_bytes = await request.body

    # Get signature from headers
    chapa_signature = request.headers.get("chapa-signature")
    x_chapa_signature = request.headers.get("x-chapa-signature")

    if not chapa_signature and not x_chapa_signature:
        return JsonResponse({"detail": "Missing signature"}, status=401)

    expected_signature = hmac.new(
        CHAPA_WEBHOOK_SECRET.encode(),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    if expected_signature not in [chapa_signature, x_chapa_signature]:
        return JsonResponse({"detail": "Invalid signature"}, status=401)

    data = json.loads(body_bytes.decode())
    tx_ref = data.get("tx_ref")
    event_type = data.get("event")
    webhook_status = data.get("status")

    if event_type != "charge.success" or webhook_status != "success":
        return JsonResponse({"status": "ignored", "reason": "non-success event"}, status=200)

    # Verify with Chapa server to be sure
    async with httpx.AsyncClient() as client:
        verify_response = await client.get(
            f"{CHAPA_VERIFY_URL}/{tx_ref}",
            headers={"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
        )
        verify_data = verify_response.json()

    if verify_data.get("status") != "success":
        return JsonResponse({"detail": "Payment verification failed"}, status=400)

    transaction_status = verify_data.get("data", {}).get("status")
    paid_amount_str = verify_data.get("data", {}).get("amount")

    if transaction_status != "success" or not paid_amount_str:
        return JsonResponse({"detail": f"Transaction not successful or missing amount"}, status=400)

    try:
        paid_amount = Decimal(paid_amount_str)
    except (TypeError, ValueError, Decimal.InvalidOperation):
        return JsonResponse({"detail": "Invalid amount received from Chapa"}, status=400)

    # Update invoice
    invoice = await sync_to_async(get_object_or_404)(Invoice, tx_ref=tx_ref)

    if invoice.status != "paid":
        invoice.amount -= paid_amount
        if invoice.amount <= 0:
            invoice.amount = 0
            invoice.status = "paid"

        await sync_to_async(invoice.save)()
        await send_notification_to_user(invoice.patient, f"Your payment of ${paid_amount} has been received.")

    return JsonResponse({"status": "success", "message": "Payment confirmed"})


@billings_router.put("/approve/{user_id}", response={200: dict, 400: dict}, auth=AuthBearer())
def approve_payment(request, user_id: int, payload: InvoiceUpdate):
    # Cashier manually approves payments after confirmation
    user = request.auth

    # Check if the user is a cashier
    if user.role != "cashier":
        return 400, {"error": "Only cashiers can approve payments"}

    # Retrieve the unpaid invoices for the given user
    invoices = Invoice.objects.filter(patient__id=user_id, status="pending")

    if not invoices:
        return 400, {"error": "No paid invoices found for this user"}

    # Calculate the total amount for all the unpaid invoices
    total_amount = sum(invoice.amount for invoice in invoices)

    # Validate if the provided amount matches the total amount of the invoices
    if payload.amount != total_amount:
        return 400, {"error": f"The provided amount ({payload.amount}) does not match the total paid invoices amount (${total_amount})"}

    # Update the status of all invoices to 'approved'
    invoices.update(status="approved")

    patient = get_object_or_404(User, id=user_id, role="patient")
    # Notify the patient that their payment has been approved
    send_notification_to_user(patient, f"Your total payment of ${total_amount} has been approved.")

    # Return the confirmation
    return {"message": f"Payment for user {user_id} approved. Total amount: ${total_amount}", "status": "approved"}
    
