from ninja import NinjaAPI
from users.views import router as user_router
from appointments.views import router as appointment_router

api = NinjaAPI(title="Hospital Management API")

# Register the routers correctly
api.add_router("/users", user_router)
api.add_router("/appointments", appointment_router)
