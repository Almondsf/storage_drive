from django.urls import path
from .views import (
    FileUploadView, FileListView, FileDownloadView,
    FileDeleteView, FileMoveView,
    FolderListCreateView, FolderDetailView,
    ShareFileView, SharedLinkListView,
    SharedLinkRevokeView, SharedFileAccessView,
    PublicSharedFileView,
)

urlpatterns = [
    # Folders
    path("folders/", FolderListCreateView.as_view(), name="folder-list-create"),
    path("folders/<uuid:pk>/", FolderDetailView.as_view(), name="folder-detail"),

    # Files
    path("files/", FileListView.as_view(), name="file-list"),
    path("files/upload/", FileUploadView.as_view(), name="file-upload"),
    path("files/<uuid:pk>/", FileDeleteView.as_view(), name="file-delete"),
    path("files/<uuid:pk>/download/", FileDownloadView.as_view(), name="file-download"),
    path("files/<uuid:pk>/move/", FileMoveView.as_view(), name="file-move"),

    # Sharing
    path("files/<uuid:pk>/share/", ShareFileView.as_view(), name="file-share"),
    path("files/<uuid:pk>/shares/", SharedLinkListView.as_view(), name="file-shares"),
    path("files/<uuid:pk>/shared/", SharedFileAccessView.as_view(), name="file-shared-access"),
    path("shares/<uuid:token>/revoke/", SharedLinkRevokeView.as_view(), name="share-revoke"),

    # Public
    path("shared/<uuid:token>/", PublicSharedFileView.as_view(), name="shared-file"),
]