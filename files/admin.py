from django.contrib import admin
from .models import Folder, File, SharedLink

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "parent", "is_deleted", "created_at")
    list_filter = ("is_deleted",)
    search_fields = ("name", "owner__username")

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "folder", "size", "mime_type", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("name", "owner__username")

@admin.register(SharedLink)
class SharedLinkAdmin(admin.ModelAdmin):
    list_display = ("file", "created_by", "permission", "expires_at", "token")