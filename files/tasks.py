from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_deleted_files():
    """
    Permanently deletes files that have been soft-deleted
    for more than 30 days.
    """
    from .models import File
    from django.core.files.storage import default_storage

    cutoff = timezone.now() - timezone.timedelta(days=30)

    old_deleted_files = File.objects.filter(
        is_deleted=True,
        deleted_at__lt=cutoff
    )

    count = 0
    for file_obj in old_deleted_files:
        try:
            # Delete from storage (local disk or R2)
            if file_obj.file and default_storage.exists(file_obj.file.name):
                default_storage.delete(file_obj.file.name)

            # Hard delete the DB row
            file_obj.delete()
            count += 1
        except Exception as e:
            logger.error(f"Failed to delete file {file_obj.id}: {e}")

    logger.info(f"Cleanup complete: {count} files permanently deleted.")
    return f"{count} files deleted"


@shared_task
def send_share_notification(file_id, shared_with_id, permission, sharer_username):
    """
    Sends an email to a user when a file is shared with them.
    """
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail
    from .models import File

    User = get_user_model()

    try:
        file_obj = File.objects.get(id=file_id, is_deleted=False)
        recipient = User.objects.get(id=shared_with_id)
    except (File.DoesNotExist, User.DoesNotExist):
        logger.warning(f"share_notification: file {file_id} or user {shared_with_id} not found")
        return

    permission_label = {
        "view": "view only",
        "download": "view and download",
        "edit": "view, download, and edit",
    }.get(permission, permission)

    send_mail(
        subject=f"{sharer_username} shared a file with you",
        message=(
            f"Hi {recipient.username},\n\n"
            f"{sharer_username} has shared '{file_obj.name}' with you.\n"
            f"Access level: {permission_label}\n\n"
            f"Log in to your account to access it."
        ),
        from_email="noreply@storagedrive.com",
        recipient_list=[recipient.email],
        fail_silently=False,
    )

    logger.info(f"Share notification sent to {recipient.email} for file {file_obj.name}")
    return f"Notification sent to {recipient.email}"