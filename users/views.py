from ninja import NinjaAPI
from ninja.security import HttpBearer
from django.contrib.auth import authenticate, login, logout
from .models import (
    User, ManagerProfile, DoctorProfile, PatientProfile,
    PharmacistProfile, LabTechnicianProfile, CashierProfile
)
from .schemas import (LoginSchema,SignupSchema,
    UserOut, ManagerProfileOut, ManagerProfileUpdate,
    DoctorProfileOut, DoctorProfileUpdate, PatientProfileOut,
    PatientProfileUpdate, PharmacistProfileOut, PharmacistProfileUpdate,
    LabTechnicianProfileOut, LabTechnicianProfileUpdate,
    CashierProfileOut, CashierProfileUpdate
)

api = NinjaAPI()

# Authentication
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = User.objects.filter(auth_token=token).first()
        return user if user else None


# Signup
@api.post("/signup/", response={200: UserOut, 400: dict})
def signup(request, payload: SignupSchema):
    if User.objects.filter(email=payload.email).exists():
        return 400, {"error": "Email already exists"}

    # Create the user
    user = User.objects.create_user(
        email=payload.email,
        password=payload.password,
        role=payload.role
    )
    return 200, user # UserOut.model_validate(user)

# Login
@api.post("/login/", response={200: dict, 401: dict})
def user_login(request, payload: LoginSchema):
    user = authenticate(request, email=payload.email, password=payload.password)
    if user:
        login(request, user)
        return 200, {"message": "Login successful", "user_id": user.id}
    return 401, {"error": "Invalid credentials"}


# Logout
@api.post("/logout/", response={200: dict})
def user_logout(request):
    logout(request)
    return 200, {"message": "Logout successful"}


# Role-to-Profile Map
ROLE_TO_PROFILE_MAP = {
    'manager': (ManagerProfile, ManagerProfileOut, ManagerProfileUpdate),
    'doctor': (DoctorProfile, DoctorProfileOut, DoctorProfileUpdate),
    'patient': (PatientProfile, PatientProfileOut, PatientProfileUpdate),
    'pharmacist': (PharmacistProfile, PharmacistProfileOut, PharmacistProfileUpdate),
    'lab_technician': (LabTechnicianProfile, LabTechnicianProfileOut, LabTechnicianProfileUpdate),
    'cashier': (CashierProfile, CashierProfileOut, CashierProfileUpdate),
}


# Profile CRUD
@api.get("/profile/", response={200: dict, 404: dict}, auth=AuthBearer())
def get_profile(request):
    user = request.auth
    role_data = ROLE_TO_PROFILE_MAP.get(user.role)

    if not role_data:
        return 404, {"error": "Profile not found"}

    profile_model, profile_out_schema, _ = role_data
    profile = profile_model.objects.filter(user=user).first()

    if profile:
        return 200, {"profile": profile_out_schema.from_orm(profile).dict()}
    return 404, {"error": "Profile not found"}


@api.put("/profile/", response={200: dict, 400: dict, 404: dict}, auth=AuthBearer())
def update_profile(request, payload: dict):
    user = request.auth
    role_data = ROLE_TO_PROFILE_MAP.get(user.role)

    if not role_data:
        return 404, {"error": "Profile not found"}

    profile_model, _, update_schema_cls = role_data
    profile = profile_model.objects.filter(user=user).first()

    if profile:
        try:
            update_schema = update_schema_cls(**payload)

            # Validate SSN for roles other than "patient"
            if user.role != 'patient' and not payload.get('ssn'):
                return 400, {"error": "SSN is required for employee profiles"}

        except Exception as e:
            return 400, {"error": str(e)}

        for attr, value in update_schema.dict(exclude_unset=True).items():
            setattr(profile, attr, value)
        profile.save()
        return 200, {"message": "Profile updated successfully"}
    return 404, {"error": "Profile not found"}


@api.delete("/profile/", response={200: dict, 404: dict}, auth=AuthBearer())
def delete_profile(request):
    user = request.auth
    role_data = ROLE_TO_PROFILE_MAP.get(user.role)

    if not role_data:
        return 404, {"error": "Profile not found"}

    profile_model, _, _ = role_data
    profile = profile_model.objects.filter(user=user).first()

    if profile:
        profile.delete()
        return 200, {"message": "Profile deleted successfully"}
    return 404, {"error": "Profile not found"}
