from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   
    TokenRefreshView,      
    TokenBlacklistView,  
)
from .views import RegisterView, MeView

urlpatterns = [
    # Registration
    path("register/", RegisterView.as_view(), name="auth-register"),

    # Login 
    path("token/", TokenObtainPairView.as_view(), name="token-obtain"),

    # Refresh access token
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Logout — blacklists the refresh token
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token-blacklist"),

    # Get current user profile
    path("me/", MeView.as_view(), name="auth-me"),
]