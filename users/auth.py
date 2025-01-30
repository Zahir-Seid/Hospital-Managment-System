from ninja_jwt.authentication import JWTAuth, AsyncJWTAuth

# Separate authentication classes for sync & async views
class AuthBearer(JWTAuth):  # Sync Auth
    pass  

class AsyncAuthBearer(AsyncJWTAuth):  # Async Auth
    pass  