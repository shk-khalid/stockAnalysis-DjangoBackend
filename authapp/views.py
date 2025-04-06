from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer

# Registration view using JWT tokens
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generate JWT tokens for the new user
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": serializer.data,
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Login view using JWT tokens
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")
            password = serializer.validated_data.get("password")
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
            
            if not user.check_password(password):
                return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": {
                    "name": f"{user.first_name} {user.last_name}".strip(),
                    "email": user.email
                },
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Logout view using JWT token blacklisting (requires simplejwt.token_blacklist app)
class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Requires token blacklisting enabled
            return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
        