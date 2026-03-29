from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from drf_spectacular.utils import extend_schema
from .views import RegisterView, MeView

# Patch the SimpleJWT views with better descriptions
TokenObtainPairView = extend_schema(
    tags=["Auth"],
    summary="Login",
    description="Authenticate with username and password. Returns an access token (15min) and refresh token (7 days).",
)(TokenObtainPairView)

TokenRefreshView = extend_schema(
    tags=["Auth"],
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token.",
)(TokenRefreshView)

TokenBlacklistView = extend_schema(
    tags=["Auth"],
    summary="Logout",
    description="Blacklist the refresh token. The user is effectively logged out.",
)(TokenBlacklistView)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token-blacklist"),
    path("me/", MeView.as_view(), name="auth-me"),
]