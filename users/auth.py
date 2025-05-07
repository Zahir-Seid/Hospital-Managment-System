from ninja_jwt.authentication import JWTAuth, AsyncJWTAuth
from django.http import HttpRequest

# Sync Auth with cookie-based token retrieval
class AuthBearer(JWTAuth):
    def get_authorization(self, request: HttpRequest):
        # Look for the token in cookies instead of headers
        token = request.COOKIES.get('access_token')
        return token


# Async Auth with cookie-based token retrieval
class AsyncAuthBearer(AsyncJWTAuth):
    async def get_authorization(self, request: HttpRequest):
        # Look for the token in cookies instead of headers
        token = request.COOKIES.get('access_token')
        return token
