from ninja import NinjaAPI
from ninja_jwt.routers.blacklist import blacklist_router
from ninja_jwt.routers.obtain import obtain_pair_router, sliding_router
from ninja_jwt.routers.verify import verify_router
from users.views import router as user_router
from appointments.views import router as appointment_router
from lab.views import lab_router
from pharmacy.views import pharmacy_router
from notifications.views import notifications_router
from billings.views import billings_router
from patients.views import patients_router
from managment.views import managment_router

api = NinjaAPI(title="Hospital Management API")

# Register the routers correctly
api.add_router("/users", user_router)
api.add_router("/appointments", appointment_router)
api.add_router("/lab", lab_router)
api.add_router("/pharmacy", pharmacy_router)
api.add_router("/notifications", notifications_router)
api.add_router("/billings", billings_router)
api.add_router("/patients", patients_router)
api.add_router("/Managment", managment_router)

# Token Management
api.add_router('/token', obtain_pair_router)  # Generates access & refresh tokens
api.add_router("/token/refresh", sliding_router)  # Added missing refresh token router
api.add_router("/token/verify", verify_router)  # Verify access tokens
api.add_router("/token/blacklist", blacklist_router)  # Blacklist refresh tokens
