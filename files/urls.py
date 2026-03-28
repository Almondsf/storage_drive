from django.urls import path
from .views import (
    FileUploadView, FileListView, FileDownloadView,
    FileDeleteView, FileMoveView,
    FolderListCreateView, FolderDetailView,
)

urlpatterns = [
    # Folder endpoints
    path("folders/", FolderListCreateView.as_view(), name="folder-list-create"),
    path("folders/<uuid:pk>/", FolderDetailView.as_view(), name="folder-detail"),

    # File endpoints
    path("files/", FileListView.as_view(), name="file-list"),
    path("files/upload/", FileUploadView.as_view(), name="file-upload"),
    path("files/<uuid:pk>/", FileDeleteView.as_view(), name="file-delete"),
    path("files/<uuid:pk>/download/", FileDownloadView.as_view(), name="file-download"),
    path("files/<uuid:pk>/move/", FileMoveView.as_view(), name="file-move"),
]