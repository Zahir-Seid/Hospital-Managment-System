from ninja import Body, Router, File, Form
from ninja.files import UploadedFile
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.authentication import AsyncJWTAuth
from .auth import AuthBearer
from notifications.views import send_notification
from notifications.utils import send_notification_to_user
from notifications.schemas import NotificationCreate
from .models import (
    User, DoctorProfile, PatientProfile,
)
from .schemas import (
    LoginSchema, SignupSchema, UserOut, DoctorProfileOut, DoctorProfileUpdate, PatientProfileOut, PatientProfileUpdate,
    CreateemployeeSchema, TokenSchema, ApprovePayload
)
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.dateparse import parse_date
from django.contrib.auth import get_user_model
from django.db.models import Q
from ninja import Body

router = Router(tags=["Authentication & Profiles"])

@router.post("/signup/", response={200: dict, 400: dict})
def signup(request, payload: SignupSchema = Form(...), profile_picture: UploadedFile = File(None)):
    """
    Patients can sign up but require approval.
    Employees must be created by a manager.
    """
    # Check if the username already exists in User model
    if get_user_model().objects.filter(username=payload.username).exists():
        return 400, {"error": "Username already exists"}

    # Create the User object (set as inactive for patient approval)
    user = get_user_model().objects.create(
        username=payload.username,
        password=make_password(payload.password),
        email=payload.email,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        gender=payload.gender,
        date_of_birth=parse_date(payload.date_of_birth),
        address=payload.address,
        ssn= payload.ssn,
        role="patient",  # Default to patient role
        is_active=False  # Set patient as inactive until approved by a record officer
    )

    # Create the PatientProfile and associate with the created user
    patient_profile = PatientProfile.objects.create(
        user=user,  # Link to the User model via OneToOneField
        region=payload.region,
        town=payload.town,
        kebele=payload.kebele,
        house_number=payload.house_number,
    )

    # Handle profile picture
    if profile_picture:
        try:
            # Generate unique filename with original extension
            file_ext = profile_picture.name.split('.')[-1] if '.' in profile_picture.name else ''
            profile_picture_name = f"profile_pictures/{user.username}_profile.{file_ext}"
            
            # Save the file using Django's default storage
            default_storage.save(profile_picture_name, ContentFile(profile_picture.read()))
            
            # Update user's profile picture
            user.profile_picture = profile_picture_name
            user.save()
        except Exception as e:
            return 400, {"error": f"Error saving profile picture: {str(e)}"}

    # Notify Record Officers for approval
    record_officers = get_user_model().objects.filter(role="record_officer").all()
    for officer in record_officers:
        # Create the NotificationCreate payload
        notification_payload = NotificationCreate(
            recipient_id=officer.id,
            message=f"New patient registration pending approval: {user.username}"
        )
        
        # Send the notification using the utility function
        send_notification_to_user(officer, notification_payload.message)

    return {"message": "Registration successful. Awaiting approval by a record officer."}

# Login
@router.post("/login/", response={200: dict, 401: dict})
def user_login(request, payload: LoginSchema):
    """
    Login using JWT authentication. Returns access and refresh tokens.
    """
    user = User.objects.filter(username=payload.username).first()

    if not user or not user.check_password(payload.password):
        return 401, {"error": "Invalid credentials"}

    if not user.is_active:
        return 401, {"error": "Your account is not approved yet."}

    # Generate Access & Refresh Tokens
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    # Collect the user's info, including both general and role-specific attributes
    user_info = {
        "role": user.role,
    }

    # Set the access and refresh tokens in HTTP-only cookies
    response = JsonResponse({
        "message": "Login successful",
        "user": user_info, # Return the full user info
        "access": str(access),
        "refresh": str(refresh),
    })

    # Set JWT tokens in HttpOnly, Secure cookies (Recommended to use in production with HTTPS)
    response.set_cookie(
        'access_token',
        str(access),
        httponly=False,
        secure=False,   # Should be True in production (HTTPS)
        samesite='None',  # Or 'Lax' depending on your use case
        max_age=60 * 60,
        
    )
    response.set_cookie(
        'refresh_token',
        str(refresh),
        httponly=False,
        secure=False,
        samesite='None',
        max_age=7 * 24 * 60 * 60,
    )

    return response

# Logout 
@router.post("/logout/", response={200: dict}, auth=AuthBearer())
def user_logout(request, token_data: TokenSchema):
    """
    Logout by blacklisting the refresh token.
    This prevents the user from getting a new access token.
    """
    try:
        token = RefreshToken(token_data.refresh_token)  # Notice change here
        token.blacklist()  # Blacklist the refresh token
    except Exception:
        return {"error": "Invalid or missing refresh token"}

    return {"message": "Logout successful. Refresh token has been revoked."}

# Refresh Token 
@router.post("/refresh-token/", response={200: dict, 401: dict})
async def refresh_token(request):
    # Get the refresh token from the request body (use request.json())
    body = await request.json()  # To get the body as a dictionary
    refresh_token = body.get("refresh")
    
    if not refresh_token:
        return 401, {"error": "No refresh token provided"}

    # Validate and generate a new access token using the refresh token
    try:
        # Verify the refresh token (using the method you have for your JWT validation)
        user = await RefreshToken().verify_refresh_token(refresh_token)

        # Create a new access token for the user
        new_access_token = await AsyncJWTAuth().create_token(user)

        return {"message": "Access token refreshed", "access": new_access_token, "refresh": refresh_token}
    except Exception as e:
        # Handle invalid or expired refresh token
        return 401, {"error": "Invalid or expired refresh token", "detail": str(e)}

# Manager Creates Employee Accounts 
@router.post("/create-employee/", response={200: UserOut, 400: dict}, auth=AuthBearer())
def create_employee(request, payload: CreateemployeeSchema = Form(...), profile_picture: UploadedFile = File(None)):
    if request.auth.role != "manager":
        return 400, {"error": "Only managers can create employee accounts."}

    if payload.role == "manager":
        return 400, {"error": "Managers cannot create other managers."}

    if User.objects.filter(username=payload.username).exists():
        return 400, {"error": "username already exists"}
    
    user = User.objects.create(
        username=payload.username,
        password=make_password(payload.password),
        email=payload.email,
        role=payload.role,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        gender=payload.gender,
        date_of_birth=payload.date_of_birth,
        address=payload.address,
        ssn=payload.ssn,
        is_active=True,  # Employees are active immediately
        )
    
    if payload.role == "doctor" or "Doctor":
        # Create the DoctorProfile and associate with the created user
        doctor_profile = DoctorProfile.objects.create(
            user=user,  # Link to the User model via OneToOneField
            department=payload.department,       
            level=payload.level,
        )
    # Handle profile picture
    if profile_picture:
        try:
            # Generate unique filename with original extension
            file_ext = profile_picture.name.split('.')[-1] if '.' in profile_picture.name else ''
            profile_picture_name = f"profile_pictures/{user.username}_profile.{file_ext}"
            
            # Save the file using Django's default storage
            default_storage.save(profile_picture_name, ContentFile(profile_picture.read()))
            
            # Update user's profile picture
            user.profile_picture = profile_picture_name
            user.save()
        except Exception as e:
            return 400, {"error": f"Error saving profile picture: {str(e)}"}
        
    return user

# endpoint to list the patients that are about to be reviewwd for approval
@router.get("/approve-patient", response={200: dict, 404: dict, 500: dict}, auth=AuthBearer())
def get_inactive_patients(request):
    try:
        # Query inactive users with role='patient'
        patients = User.objects.filter(role="patient", is_active=False).prefetch_related("patient_profile")

        patient_data = []
        for patient in patients:
            profile = getattr(patient, "patient_profile", None)  # Avoid errors if profile is missing
            profile_picture_url = request.build_absolute_uri(patient.profile_picture.url) if patient.profile_picture else None

            patient_data.append({
                "user_id": patient.id,
                "username": patient.username,
                "first_name": patient.first_name,
                "middle_name": patient.middle_name,
                "last_name": patient.last_name,
                "email": patient.email,
                "phone_number": patient.phone_number,
                "address": patient.address,
                "gender": patient.gender,
                "date_of_birth": patient.date_of_birth,
                "region": profile.region if profile else None,
                "town": profile.town if profile else None,
                "kebele": profile.kebele if profile else None,
                "house_number": profile.house_number if profile else None,
                "profile_picture_url": profile_picture_url,
            })

        return 200, {"patients": patient_data}

    except Exception as e:
        return 500, {"error": str(e)}

    
# Record Officer Approves Patient Signup 
@router.put("/approve-patient/", response={200: dict, 400: dict}, auth=AuthBearer())
def approve_patient(request, payload: ApprovePayload = Body(...)):
    user_id = payload.user_id

    if request.auth.role != "record_officer":
        return 400, {"error": "Only record officers can approve patients."}

    patient = User.objects.filter(id=user_id, role="patient", is_active=False).first()
    if not patient:
        return 400, {"error": "Patient not found or already approved."}

    patient.is_active = True
    patient.save()

    send_notification_to_user(
        recipient=patient,
        message="Your registration has been approved. You can now log in."
    )

    return {"message": "Patient approved successfully."}

# Profile Handling
ROLE_TO_PROFILE_MAP = {
    'doctor': (DoctorProfile, DoctorProfileOut, DoctorProfileUpdate),
    'patient': (PatientProfile, PatientProfileOut, PatientProfileUpdate),
    'user': (UserOut),
}

# Get Profile 
@router.get("/profile/", response={200: dict, 404: dict}, auth=AuthBearer())
def get_profile(request):
    user = request.auth
    role_data = ROLE_TO_PROFILE_MAP.get(user.role)

    if not role_data:
        return 404, {"error": "Profile not found"}

    profile_model, profile_out_schema, _ = role_data
    profile = profile_model.objects.filter(user=user).first()

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

        profile.save()
        return {"message": "Profile updated successfully"}
    return 404, {"error": "Profile not found"}
