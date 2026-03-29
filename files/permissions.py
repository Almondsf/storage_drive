from django.db import models as db_models
from django.utils import timezone


# Encode the hierarchy as data, not as if/elif chains.
# Adding a new tier later = update this dict, nothing else.
PERMISSION_HIERARCHY = {
    "view": 1,
    "download": 2,
    "edit": 3,
}


def has_required_permission(link_permission, required_permission):
    link_level = PERMISSION_HIERARCHY.get(link_permission, 0)
    required_level = PERMISSION_HIERARCHY.get(required_permission, 0)
    return link_level >= required_level


def get_valid_share_link(file_obj, user, required_permission="view"):
    from .models import SharedLink

    candidates = SharedLink.objects.filter(
        file=file_obj,
        shared_with=user,
    ).filter(
        # Either no expiry, or expiry is in the future
        db_models.Q(expires_at__isnull=True) |
        db_models.Q(expires_at__gt=timezone.now())
    )

    for link in candidates:
        if has_required_permission(link.permission, required_permission):
            return link

    return None


class IsOwner:
    message = "You do not have permission to access this resource."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user