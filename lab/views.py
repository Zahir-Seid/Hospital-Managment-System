from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import LabTest
from .schemas import LabTestCreate, LabTestUpdate, LabTestOut
from users.views import AuthBearer  

lab_router = Router(tags=["Lab Tests"], auth=AuthBearer())

# Doctor orders a lab test
@lab_router.post("/order", response={200: LabTestOut, 400: dict})
def order_lab_test(request, payload: LabTestCreate):
    """
    Doctor orders a lab test for a patient.
    """
    doctor = request.auth  

    if doctor.role != "doctor":
        return 400, {"error": "Only doctors can order lab tests"}

    patient = get_object_or_404(User, id=payload.patient_id, role="patient")

    lab_test = LabTest.objects.create(
        doctor=doctor,
        patient=patient,
        test_name=payload.test_name
    )
    return lab_test


# List lab tests (for patient, doctor, or lab technician)
@lab_router.get("/list", response={200: list[LabTestOut]})
def list_lab_tests(request):
    """
    Retrieve lab tests for the logged-in user.
    - Doctors see tests they ordered.
    - Patients see their own tests.
    - Lab technicians see all tests.
    """
    user = request.auth

    if user.role == "doctor":
        tests = LabTest.objects.filter(doctor=user)
    elif user.role == "patient":
        tests = LabTest.objects.filter(patient=user)
    elif user.role == "lab_technician":
        tests = LabTest.objects.all()
    else:
        return []

    return tests


# Lab Technician updates test status and result
@lab_router.put("/update/{lab_test_id}", response={200: LabTestOut, 400: dict})
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
    return lab_test
