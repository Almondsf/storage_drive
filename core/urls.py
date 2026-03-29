from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,       # serves the raw schema as JSON/YAML
    SpectacularSwaggerView,   # serves the Swagger UI (interactive browser)
    SpectacularRedocView,     # serves ReDoc (cleaner read-only alternative)
)

urlpatterns = [
    path("admin/", admin.site.urls),
    
        # Raw OpenAPI schema — download this as JSON or YAML
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI — interactive, try endpoints live
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # ReDoc — cleaner read-only alternative to Swagger
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),


    path("api/auth/", include("accounts.urls")),
    path("api/", include("files.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)