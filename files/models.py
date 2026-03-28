import uuid
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings



class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)      

    class Meta:
        abstract = True
        
class Folder(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,      
        related_name="folders"
    )
    parent = models.ForeignKey(
        "self",                          
        null=True,
        blank=True,
        on_delete=models.CASCADE,        
        related_name="subfolders"
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("owner", "parent", "name")

    def __str__(self):
        return f"{self.owner.username}/{self.name}"
    

class File(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="files"
    )
    folder = models.ForeignKey(
        Folder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,       
        related_name="files"
    )
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    size = models.PositiveBigIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=255, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("owner", "folder", "name")

    def __str__(self):
        return f"{self.owner.username}/{self.name}"
    

class SharedLink(models.Model):

    PERMISSION_CHOICES = [
        ("view", "View only"),       # metadata only
        ("download", "Download"),    # view + download
        ("edit", "Edit"),            # view + download + modify
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(
        "File",
        on_delete=models.CASCADE,
        related_name="shared_links"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shared_links"
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="received_links"
        # null = public link, a user = specific user share
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    permission = models.CharField(
        max_length=10,
        choices=PERMISSION_CHOICES,
        default="view"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Link:{self.token} → {self.file.name} ({self.permission})"