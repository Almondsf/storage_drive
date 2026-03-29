import os
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from .models import File, Folder, SharedLink
from .permissions import IsOwner, get_valid_share_link
from .serializers import FileUploadSerializer, FileListSerializer, FolderSerializer, FolderCreateSerializer, SharedLinkCreateSerializer, SharedLinkSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    tags=["Files"],
    summary="Upload a file",
    description=(
        "Upload a file using multipart/form-data. "
        "Optionally provide a folder UUID to place the file inside a folder. "
        "Omit folder to place at root level."
    ),
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary"},
                "folder": {"type": "string", "format": "uuid", "nullable": True},
            },
            "required": ["file"],
        }
    },
    responses={
        201: FileUploadSerializer,
        400: OpenApiResponse(description="Validation error — file too large or type not allowed"),
    },
)
class FileUploadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes_override = None 

    def post(self, request):
        serializer = FileUploadSerializer(
            data=request.data,
            context={"request": request}  
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=["Files"],
    summary="List files",
    description="Returns files owned by the authenticated user. Defaults to root level files.",
    parameters=[
        OpenApiParameter(
            name="folder",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by folder UUID. Omit for root level files.",
            required=False,
        )
    ],
    responses={200: FileListSerializer(many=True)},
)
class FileListView(generics.ListAPIView):
    serializer_class = FileListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Base queryset — only this user's non-deleted files
        queryset = File.objects.filter(
            owner=self.request.user,
            is_deleted=False
        )

        # Optional folder filter via query param: /api/files/?folder=<uuid>
        folder_id = self.request.query_params.get("folder")
        if folder_id:
            queryset = queryset.filter(folder__id=folder_id)
        else:
            # No folder param = root level files
            queryset = queryset.filter(folder=None)

        return queryset

@extend_schema(
    tags=["Files"],
    summary="Download a file",
    description="Streams the file content. Only the file owner can use this endpoint.",
    responses={
        200: OpenApiResponse(description="File stream with correct Content-Type header"),
        404: OpenApiResponse(description="File not found or not owned by user"),
    },
)
class FileDownloadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        # get_object_or_404 returns 404 if not found — cleaner than try/except
        file_obj = get_object_or_404(
            File,
            pk=pk,
            owner=request.user,     # users can only download their own files
            is_deleted=False
        )

        # Open the file in binary read mode
        file_handle = file_obj.file.open("rb")

        response = FileResponse(
            file_handle,
            content_type=file_obj.mime_type or "application/octet-stream"
        )

        # Content-Disposition tells the browser to download, not display
        response["Content-Disposition"] = f'attachment; filename="{file_obj.name}"'
        response["Content-Length"] = file_obj.size

        return response
 
@extend_schema(tags=["Files"])   
class FileDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        file_obj = get_object_or_404(File, pk=pk, owner=request.user, is_deleted=False)

        from django.utils import timezone
        file_obj.is_deleted = True
        file_obj.deleted_at = timezone.now()
        file_obj.save(update_fields=["is_deleted", "deleted_at"])
        # update_fields tells Django to only UPDATE those two columns
        # instead of writing the entire row — more efficient

        return Response({"detail": "File moved to trash."}, status=status.HTTP_200_OK)

@extend_schema(tags=["Folders"])    
class FolderListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FolderCreateSerializer
        return FolderSerializer
    
    def get_queryset(self):
        user = self.request.user
        parent_id = self.request.query_params.get("parent")

        queryset = Folder.objects.filter(
            owner=user,
            is_deleted=False
        ).prefetch_related(
            "subfolders",
            "files"
        )
        
        if parent_id:
            queryset = queryset.filter(parent__id=parent_id)
        else:
            queryset = queryset.filter(parent=None)

        return queryset

@extend_schema(tags=["Folders"])
class FolderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return FolderCreateSerializer
        return FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(
            owner=self.request.user,
            is_deleted=False
        ).prefetch_related("subfolders", "files")

    def perform_destroy(self, instance):
        from django.utils import timezone

        # Soft delete the folder itself
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at"])

        # Recursively soft delete all subfolders
        self._soft_delete_children(instance, timezone.now())

    def _soft_delete_children(self, folder, now):
        for subfolder in folder.subfolders.filter(is_deleted=False):
            subfolder.is_deleted = True
            subfolder.deleted_at = now
            subfolder.save(update_fields=["is_deleted", "deleted_at"])
            self._soft_delete_children(subfolder, now)

        # Also soft delete files directly in this folder
        folder.files.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=now
        )
        
@extend_schema(tags=["Files"])        
class FileMoveView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        file_obj = get_object_or_404(File, pk=pk, owner=request.user, is_deleted=False)

        # folder can be null (move to root) or a folder uuid
        folder_id = request.data.get("folder")

        if folder_id:
            folder = get_object_or_404(
                Folder,
                pk=folder_id,
                owner=request.user,     # can only move into your own folders
                is_deleted=False
            )
            file_obj.folder = folder
        else:
            file_obj.folder = None      # move to root

        file_obj.save(update_fields=["folder"])
        return Response(
            FileListSerializer(file_obj).data,
            status=status.HTTP_200_OK
        )


from .permissions import IsOwner, get_valid_share_link
from .serializers import SharedLinkCreateSerializer, SharedLinkSerializer

@extend_schema(tags=["Sharing"])
class ShareFileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        file_obj = get_object_or_404(File, pk=pk, is_deleted=False)

        # Manual ownership check — only owner can share
        if file_obj.owner != request.user:
            return Response(
                {"detail": "You do not own this file."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SharedLinkCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            link = serializer.save(file=file_obj, created_by=request.user)
            return Response(
                SharedLinkSerializer(link, context={"request": request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=["Sharing"])
class SharedLinkListView(generics.ListAPIView):
    serializer_class = SharedLinkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        file_obj = get_object_or_404(
            File,
            pk=self.kwargs["pk"],
            owner=self.request.user,
            is_deleted=False
        )
        return SharedLink.objects.filter(file=file_obj).order_by("-created_at")

@extend_schema(tags=["Sharing"])
class SharedLinkRevokeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, token):
        link = get_object_or_404(
            SharedLink,
            token=token,
            created_by=request.user
        )
        link.delete()
        return Response(
            {"detail": "Share link revoked."},
            status=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Sharing"],
    summary="Access a shared file",
    description=(
        "Access a file shared with the authenticated user. "
        "Response depends on permission tier: "
        "'view' returns metadata only. "
        "'download' or 'edit' streams the file."
    ),
    responses={
        200: OpenApiResponse(description="File metadata (view) or file stream (download/edit)"),
        403: OpenApiResponse(description="No valid share link found for this user"),
    },
)
class SharedFileAccessView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        file_obj = get_object_or_404(File, pk=pk, is_deleted=False)

        # Owners always have full access
        if file_obj.owner == request.user:
            return self._stream_file(file_obj)

        # Find the best valid link for this user
        # Start by checking if they have at least view access
        link = get_valid_share_link(file_obj, request.user, required_permission="view")

        if not link:
            return Response(
                {"detail": "You do not have access to this file."},
                status=status.HTTP_403_FORBIDDEN
            )

        # view only — return metadata, not the file
        if link.permission == "view":
            return Response(FileListSerializer(file_obj).data)

        # download or edit — stream the file
        return self._stream_file(file_obj)

    def _stream_file(self, file_obj):
        file_handle = file_obj.file.open("rb")
        response = FileResponse(
            file_handle,
            content_type=file_obj.mime_type or "application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{file_obj.name}"'
        response["Content-Length"] = file_obj.size
        return response

@extend_schema(
    tags=["Sharing"],
    summary="Public shared file access",
    description=(
        "Access a file via a public share token. No authentication required for public links. "
        "User-specific links require the correct authenticated user. "
        "Returns metadata for 'view' links, streams file for 'download'/'edit' links."
    ),
    parameters=[
        OpenApiParameter(
            name="token",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="The share token from the share link URL.",
        )
    ],
    responses={
        200: OpenApiResponse(description="File metadata or file stream"),
        401: OpenApiResponse(description="Authentication required for user-specific link"),
        403: OpenApiResponse(description="This link was not shared with you"),
        410: OpenApiResponse(description="Share link has expired"),
    },
    auth=[],  # marks this endpoint as public in Swagger UI — no lock icon
)
class PublicSharedFileView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        link = get_object_or_404(SharedLink, token=token)

        # Check expiry
        if link.expires_at and link.expires_at <= timezone.now():
            return Response(
                {"detail": "This share link has expired."},
                status=status.HTTP_410_GONE
            )

        # User-specific link validation
        if link.shared_with:
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Please log in to access this link."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            if request.user != link.shared_with:
                return Response(
                    {"detail": "This link was not shared with you."},
                    status=status.HTTP_403_FORBIDDEN
                )

        file_obj = link.file

        # view only — metadata, no file
        if link.permission == "view":
            return Response(FileListSerializer(file_obj).data)

        # download or edit — stream the file
        file_handle = file_obj.file.open("rb")
        response = FileResponse(
            file_handle,
            content_type=file_obj.mime_type or "application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{file_obj.name}"'
        response["Content-Length"] = file_obj.size
        return response