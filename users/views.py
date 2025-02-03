from ninja import Router
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.authentication import AsyncJWTAuth
from .auth import AsyncAuthBearer, AuthBearer
from notifications.views import send_notification
from .models import (
    User, ManagerProfile, DoctorProfile, PatientProfile,
    PharmacistProfile, LabTechnicianProfile, CashierProfile
)
from .schemas import (
    LoginSchema, SignupSchema, UserOut, ManagerProfileOut, ManagerProfileUpdate,
    DoctorProfileOut, DoctorProfileUpdate, PatientProfileOut, PatientProfileUpdate,
    PharmacistProfileOut, PharmacistProfileUpdate, LabTechnicianProfileOut, LabTechnicianProfileUpdate,
    CashierProfileOut, CashierProfileUpdate, CreateemployeeSchema
)

router = Router(tags=["Authentication & Profiles"])

# Signup
@router.post("/signup/", response={200: dict, 400: dict})
def signup(request, payload: SignupSchema):
    """
    Patients can sign up but require approval.
    Employees must be created by a manager.
    """

    if User.objects.filter(username=payload.username).exists():
        return 400, {"error": "Username already exists"}

    user = User.objects.create(
        username=payload.username,
        password=make_password(payload.password),
        role="patient",
        is_active=False  # Patients require approval
    )

    # Notify Record Officers
    record_officers = User.objects.filter(role="record_officer").all()
    for officer in record_officers:
        send_notification(officer, f"New patient registration pending approval: {user.username}")

    return {"message": "Registration successful. Awaiting approval by a record officer."}

# Login
@router.post("/login/", response={200: dict, 401: dict})
def user_login(request, payload: LoginSchema):
    """
    Login using JWT authentication. Returns access and refresh tokens.
    """
    user = User.objects.filter(username=payload.username).afirst()
    if not user or not user.check_password(payload.password):
        return 401, {"error": "Invalid credentials"}

    if not user.is_active:
        return 401, {"error": "Your account is not approved yet."}

    # Generate Access & Refresh Tokens
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    return {
        "message": "Login successful",
        "access": str(access),  # Short-lived access token
        "refresh": str(refresh),  # Long-lived refresh token
    }


# Logout 
@router.post("/logout/", response={200: dict}, auth=AuthBearer())
def user_logout(request, refresh_token: str):
    """
    Logout by blacklisting the refresh token.
    This prevents the user from getting a new access token.
    """
    try:
        token = RefreshToken(refresh_token)  # Get token from request body
        token.blacklist()  # Blacklist the refresh token
    except Exception:
        return {"error": "Invalid or missing refresh token"}

    return {"message": "Logout successful. Refresh token has been revoked."}

# Refresh Token 
@router.post("/refresh-token/", response={200: dict, 401: dict})
async def refresh_token(request):
    refresh_token = request.data.get("refresh_token")
    if not refresh_token:
        return 401, {"error": "No refresh token provided"}

    # Validate and generate a new access token using the refresh token
    try:
        user = await RefreshToken().verify_refresh_token(refresh_token)
        new_access_token = await AsyncJWTAuth().create_token(user)
        return {"message": "Access token refreshed", "access_token": new_access_token}
    except Exception:
        return 401, {"error": "Invalid or expired refresh token"}

# Manager Creates Employee Accounts 
@router.post("/create-employee/", response={200: UserOut, 400: dict}, auth=AuthBearer())
async def create_employee(request, payload: CreateemployeeSchema):
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can create employee accounts."}

    if payload.role == "manager":
        return 400, {"error": "Managers cannot create other managers."}

    if await User.objects.filter(username=payload.username).aexists():
        return 400, {"error": "username already exists"}

    user = await User.objects.acreate(
        username=payload.username,
        password=make_password(payload.password),
        role=payload.role,
        is_active=True  # Employees are active immediately
    )

    return user


# Record Officer Approves Patient Signup 
@router.put("/approve-patient/{user_id}/", response={200: dict, 400: dict}, auth=AsyncAuthBearer())
async def approve_patient(request, user_id: int):
    if request.auth.role != "record_officer":
        return 400, {"error": "Only record officers can approve patients."}

    patient = await get_object_or_404(User.objects.filter(id=user_id, role="patient", is_active=False))
    patient.is_active = True
    await patient.asave()

    await send_notification(patient, "Your registration has been approved. You can now log in.")
    return {"message": "Patient approved successfully."}

# Profile Handling
ROLE_TO_PROFILE_MAP = {
    'manager': (ManagerProfile, ManagerProfileOut, ManagerProfileUpdate),
    'doctor': (DoctorProfile, DoctorProfileOut, DoctorProfileUpdate),
    'patient': (PatientProfile, PatientProfileOut, PatientProfileUpdate),
    'pharmacist': (PharmacistProfile, PharmacistProfileOut, PharmacistProfileUpdate),
    'lab_technician': (LabTechnicianProfile, LabTechnicianProfileOut, LabTechnicianProfileUpdate),
    'cashier': (CashierProfile, CashierProfileOut, CashierProfileUpdate),
}

# Get Profile 
@router.get("/profile/", response={200: dict, 404: dict}, auth=AuthBearer())
def get_profile(request):
    user = request.auth
    role_data = ROLE_TO_PROFILE_MAP.get(user.role)

    if not role_data:
        return 404, {"error": "Profile not found"}

    profile_model, profile_out_schema, _ = role_data
    profile = profile_model.objects.filter(user=user).afirst()

    if profile:
        return {"profile": profile_out_schema.model_validate(profile)}
    return 404, {"error": "Profile not found"}

# Update Profile 
@router.put("/profile/", response={200: dict, 400: dict, 404: dict}, auth=AuthBearer())
def update_profile(request, payload: dict):
    user = request.auth
    role_data = ROLE_TO_PROFILE_MAP.get(user.role)

    if not role_data:
        return 404, {"error": "Profile not found"}

    profile_model, _, update_schema_cls = role_data
    profile = profile_model.objects.filter(user=user).afirst()

    if profile:
        update_schema = update_schema_cls.model_validate(payload)
        if user.role != 'patient' and not payload.get('ssn'):
            return 400, {"error": "SSN is required for employee profiles"}

        for attr, value in update_schema.dict(exclude_unset=True).items():
            setattr(profile, attr, value)

        profile.asave()
        return {"message": "Profile updated successfully"}
    return 404, {"error": "Profile not found"}

# Delete Profile 
@router.delete("/profile/", response={200: dict, 404: dict}, auth=AuthBearer())
def delete_profile(request):
    user = request.auth
    role_data = ROLE_TO_PROFILE_MAP.get(user.role)

    if not role_data:
        return 404, {"error": "Profile not found"}

    profile_model, _, _ = role_data
    profile = profile_model.objects.filter(user=user).afirst()

    if profile:
        profile.delete()
        #user.delete()
        return 200, {"message": "Profile deleted successfully"}
    return 404, {"error": "Profile not found"}
