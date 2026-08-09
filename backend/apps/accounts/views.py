"""
Accounts views.

Endpoints:
  POST  /api/auth/register/        — Create account
  POST  /api/auth/login/           — JWT token pair
  POST  /api/auth/refresh/         — Refresh access token
  POST  /api/auth/logout/          — Blacklist refresh token
  GET   /api/auth/me/              — Authenticated user profile
  PATCH /api/auth/me/              — Update profile
  POST  /api/auth/change-password/ — Change password
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UpdateProfileSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(APIView):
    """
    POST /api/auth/register/

    Creates a new user account. Wallet is automatically created via signal.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_data = UserSerializer(user).data
        return Response(
            {
                "success": True,
                "message": "Account created successfully. Please log in.",
                "data": user_data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Returns JWT access + refresh tokens along with user data.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            return Response(
                {
                    "success": True,
                    "message": "Login successful.",
                    "data": response.data,
                },
                status=status.HTTP_200_OK,
            )
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/auth/refresh/

    Returns a new access token using a valid refresh token.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            return Response(
                {
                    "success": True,
                    "message": "Token refreshed successfully.",
                    "data": response.data,
                },
                status=status.HTTP_200_OK,
            )
        return response


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Blacklists the provided refresh token. Requires authentication.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"success": False, "message": "Refresh token is required.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("User logged out: %s", request.user.email)
            return Response(
                {"success": True, "message": "Logged out successfully.", "data": {}},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.warning("Logout failed for %s: %s", request.user.email, e)
            return Response(
                {"success": False, "message": "Invalid or expired refresh token.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    """
    GET   /api/auth/me/ — Return authenticated user's profile.
    PATCH /api/auth/me/ — Update first_name, last_name, phone_number.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user)
        return Response(
            {
                "success": True,
                "message": "Profile retrieved successfully.",
                "data": serializer.data,
            }
        )

    def patch(self, request: Request) -> Response:
        serializer = UpdateProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "success": True,
                "message": "Profile updated successfully.",
                "data": UserSerializer(request.user).data,
            }
        )


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/

    Allows an authenticated user to change their password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "success": True,
                "message": "Password changed successfully. Please log in again.",
                "data": {},
            }
        )
