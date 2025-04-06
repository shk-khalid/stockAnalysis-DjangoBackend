import jwt
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

@database_sync_to_async
def get_user_from_token(token):
    """
    Validate the JWT token and return the user if valid.
    """
    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated_token)
        print(f"✅ User authenticated: {user}")  # Debug print
        return user
    except AuthenticationFailed:
        print("❌ Authentication failed")
        return AnonymousUser()
    except Exception as e:
        print(f"❌ JWT Error: {e}")
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token_list = query_params.get("token")  # Extract token from query params

        if token_list:
            token = token_list[0]
            print(f"🔍 Received token: {token}")  # Debug print
            scope["user"] = await get_user_from_token(token)  # Authenticate user
        else:
            print("⚠️ No token found, assigning AnonymousUser")
            scope["user"] = AnonymousUser()  # Assign anonymous user if no token

        return await super().__call__(scope, receive, send)
