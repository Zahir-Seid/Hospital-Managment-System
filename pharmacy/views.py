from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import Prescription, Drug
from .schemas import (
    PrescriptionCreate, PrescriptionUpdate, PrescriptionOut,
    DrugCreate, DrugUpdate, DrugOut
)
from users.auth import AuthBearer, AsyncAuthBearer 
from notifications.views import send_notification  

pharmacy_router = Router(tags=["Pharmacy"])

# Doctor creates a prescription
@pharmacy_router.post("/prescribe", response={200: PrescriptionOut, 400: dict}, auth=AsyncAuthBearer())
async def prescribe_medication(request, payload: PrescriptionCreate):
    """
    Doctor prescribes medication to a patient.
    """
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
        await send_notification(pharmacist, f"New prescription for {patient.username}: {payload.medication_name}.")

    return prescription


# List prescriptions (for patient, doctor, or pharmacist)
@pharmacy_router.get("/list", response={200: list[PrescriptionOut]}, auth=AuthBearer())
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

    return prescriptions


# Pharmacist updates prescription status
@pharmacy_router.put("/update/{prescription_id}", response={200: PrescriptionOut, 400: dict}, auth=AsyncAuthBearer())
async def update_prescription(request, prescription_id: int, payload: PrescriptionUpdate):
    """
    Pharmacists update prescription status (mark as dispensed).
    """
    user = request.auth

    if user.role != "pharmacist":
        return 400, {"error": "Only pharmacists can update prescription status"}

    prescription = get_object_or_404(Prescription, id=prescription_id)

    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(prescription, attr, value)

    prescription.save()

    # Notify the patient when the prescription is dispensed
    if prescription.status == "dispensed":
        await send_notification(prescription.patient, f"Your prescription for {prescription.medication_name} is ready for pickup.")

    return prescription


# Pharmacist creates a new drug
@pharmacy_router.post("/drugs/create", response={200: DrugOut, 400: dict}, auth=AuthBearer())
def create_drug(request, payload: DrugCreate):
    """
    Pharmacist adds a new drug to inventory.
    """
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
@pharmacy_router.get("/drugs/list", response={200: list[DrugOut]})
def list_drugs(request):
    """
    Retrieve all available drugs.
    """
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
