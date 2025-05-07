from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from billings.models import Invoice
from .models import Prescription, Drug
from .schemas import (
    PrescriptionCreate, PrescriptionUpdate, PrescriptionOut,
    DrugCreate, DrugUpdate, DrugOut
)
from users.auth import AuthBearer, AsyncAuthBearer 
from notifications.utils import send_notification_to_user 

pharmacy_router = Router(tags=["Pharmacy"])

# Doctor creates a prescription
@pharmacy_router.post("/prescribe", response={200: dict, 400: dict}, auth=AuthBearer())
def prescribe_medication(request, payload: PrescriptionCreate):

    # Doctor prescribes medication to a patient.
    doctor = request.auth  

    if doctor.role != "doctor":
        return 400, {"error": "Only doctors can prescribe medication"}

    patient = get_object_or_404(User, id=payload.patient_id, role="patient")

    prescription = Prescription.objects.create(
        doctor=doctor,
        patient=patient,
        medication_name=payload.medication_name,
        dosage=payload.dosage,
        instructions=payload.instructions
    )

    # Notify all pharmacists about the new prescription
    pharmacists = User.objects.filter(role="pharmacist")
    for pharmacist in pharmacists:
        send_notification_to_user(pharmacist, f"New prescription for {patient.username}: {payload.medication_name}.")

    return {
        "id": prescription.id,
        "doctor": doctor.username,
        "patient": patient.username,
        "medication_name": prescription.medication_name,
        "dosage": prescription.dosage,
        "instructions": prescription.instructions
    }



# List prescriptions (for patient, doctor, or pharmacist)
@pharmacy_router.get("/list", response={200: list[dict]}, auth=AuthBearer())
def list_prescriptions(request):
    """
    Retrieve prescriptions for the logged-in user.
    - Doctors see prescriptions they created.
    - Patients see their own prescriptions.
    - Pharmacists see all prescriptions.
    """
    user = request.auth

    if user.role == "doctor":
        prescriptions = Prescription.objects.filter(doctor=user)
    elif user.role == "patient":
        prescriptions = Prescription.objects.filter(patient=user)
    elif user.role == "pharmacist":
        prescriptions = Prescription.objects.all()
    else:
        return []

    return [
        {
            "id": p.id,
            "doctor": p.doctor.username,
            "patient": p.patient.username,
            "medication_name": p.medication_name,
            "dosage": p.dosage,
            "instructions": p.instructions,
            "status": p.status,
            "prescribed_at": p.prescribed_at,
            "updated_at": p.updated_at,
        }
        for p in prescriptions
    ]


# Pharmacist updates prescription status
@pharmacy_router.put("/update/{prescription_id}", response={200: dict, 400: dict}, auth=AuthBearer())
def update_prescription(request, prescription_id: int, payload: PrescriptionUpdate):
    user = request.auth

    if user.role != "pharmacist":
        return 400, {"error": "Only pharmacists can update prescription status"}

    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Update prescription fields from payload
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(prescription, attr, value)

    prescription.save()

    # If prescription status is dispensed, create an invoice and notify the patient
    if prescription.status == "Dispensed":
        price = payload.price

        if not price or price <= 0:
            return 400, {"error": "Invalid price for the prescription."}


        # Create an invoice using the price from the frontend
        invoice = Invoice.objects.create(
            patient=prescription.patient,
            amount=price,
            description=f"Prescription for {prescription.medication_name}",
        )

        send_notification_to_user(
            prescription.patient,
            f"Your prescription for {prescription.medication_name} is ready for pickup. An invoice of ${invoice.amount} has been generated."
        )

    return {"message": "Prescription updated successfully"}


# Pharmacist creates a new drug
@pharmacy_router.post("/drugs/create", response={200: DrugOut, 400: dict}, auth=AuthBearer())
def create_drug(request, payload: DrugCreate):
    # Pharmacist adds a new drug to inventory.

    pharmacist = request.auth  

    if pharmacist.role != "pharmacist":
        return 400, {"error": "Only pharmacists can add drugs"}

    drug = Drug.objects.create(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        stock_quantity=payload.stock_quantity
    )
    return drug


# List all drugs
@pharmacy_router.get("/drugs/list", response={200: list[DrugOut]}, auth=AuthBearer())
def list_drugs(request):
    # Retrieve all available drugs.
    pharmacist = request.auth  

    if pharmacist.role != "pharmacist":
        return 400, {"error": "Unauthorized"}

    return Drug.objects.all()


# Update drug details (only pharmacist)
@pharmacy_router.put("/drugs/update/{drug_id}", response={200: DrugOut, 400: dict}, auth=AuthBearer())
def update_drug(request, drug_id: int, payload: DrugUpdate):
    """
    Pharmacist updates drug information (stock, price, etc.).
    """
    pharmacist = request.auth

    if pharmacist.role != "pharmacist":
        return 400, {"error": "Only pharmacists can update drug details"}

    drug = get_object_or_404(Drug, id=drug_id)

    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(drug, attr, value)

    drug.save()
    return drug

# Search for a drug by name
@pharmacy_router.get("/drugs/search", response={200: list[DrugOut], 400: dict}, auth=AuthBearer())
def search_drugs(request, name: str):
    """
    Pharmacist searches for drugs by name.
    """
    if request.auth.role != "pharmacist":
        return 400, {"error": "not allowed"}

    drugs = Drug.objects.filter(name__icontains=name)
    
    if not drugs.exists():
        return 400, {"error": "No matching drugs found; please report to manager to add it"}

    return drugs

# Delete a drug (only pharmacist)
@pharmacy_router.delete("/drugs/delete/{drug_id}", response={200: dict, 400: dict}, auth=AuthBearer())
def delete_drug(request, drug_id: int):
    """
    Pharmacist deletes a drug from inventory.
    """
    pharmacist = request.auth

    if pharmacist.role != "pharmacist":
        return 400, {"error": "Only pharmacists can delete drugs"}

    drug = get_object_or_404(Drug, id=drug_id)
    drug.delete()
    return {"message": "Drug deleted successfully"}