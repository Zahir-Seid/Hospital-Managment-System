from ninja import NinjaAPI
from users.views import router as user_router
from appointments.views import router as appointment_router
from lab.views import lab_router
from pharmacy.views import pharmacy_router
from notifications.views import notifications_router
from billings.views import billings_router
from patients.views import patients_router

api = NinjaAPI(title="Hospital Management API")

# Register the routers correctly
api.add_router("/users", user_router)
api.add_router("/appointments", appointment_router)
api.add_router("/lab", lab_router)
api.add_router("/pharmacy", pharmacy_router)
api.add_router("/notifications", notifications_router)
api.add_router("/billings", billings_router)
api.add_router("/patients", patients_router)