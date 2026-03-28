import os
import mimetypes
from django.core.files.storage import default_storage
from rest_framework import serializers
from .models import File, Folder, SharedLink

class RecursiveFolderSerializer(serializers.Serializer):
    
    def to_representation(self, instance):
        serializer = FolderSerializer(instance, context=self.context)
        return serializer.data
    
class FolderSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    subfolders = RecursiveFolderSerializer(many=True, read_only=True)
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = (
            "id", "name", "parent", "owner",
            "subfolders", "file_count", "created_at"
        )
        read_only_fields = ("id", "owner", "created_at")

    def get_file_count(self, obj):
        return obj.files.filter(is_deleted=False).count()
    
class FolderCreateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Folder
        fields = ("id", "name", "parent")
        read_only_fields = ("id",)

    def validate(self, attrs):
        user = self.context["request"].user
        parent = attrs.get("parent")
        name = attrs.get("name")
        
        # Check for duplicate folder name in same location
        qs = Folder.objects.filter(owner=user, parent=parent, name=name, is_deleted=False)

        # On update, exclude current instance from uniqueness check
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "A folder with this name already exists here."}
            )

        if parent and parent.owner != user:
            raise serializers.ValidationError(
                {"parent": "You do not own this folder."}
            )

        return attrs

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)
    
class FileUploadSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = File
        fields = ("id", "name", "file", "folder", "owner", "size", "mime_type", "created_at")
        read_only_fields = ("id", "name", "owner", "size", "mime_type", "created_at")
        
    def validate_file(self, value):
        # 100MB limit
        max_size = 100 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 100MB.")

        # Block dangerous file types
        dangerous_extensions = [
            ".exe", ".bat", ".sh", ".php",
            ".js", ".py", ".rb", ".pl"
        ]
        ext = os.path.splitext(value.name)[1].lower()
        if ext in dangerous_extensions:
            raise serializers.ValidationError(f"File type '{ext}' is not allowed.")

        return value
    
    def create(self, validated_data):
        
        uploaded_file = validated_data['file']
        original_name = os.path.basename(uploaded_file.name)
        mime_type, _ = mimetypes.guess_type(original_name)
        
        validated_data["name"] = original_name
        validated_data["size"] = uploaded_file.size
        validated_data["mime_type"] = mime_type or "application/octet-stream"
        validated_data["owner"] = self.context["request"].user
        
        return super().create(validated_data)
    
class FileListSerializer(serializers.ModelSerializer):
    
    owner = serializers.StringRelatedField(read_only=True)
    folder_name = serializers.CharField(source="folder.name", read_only=True)

    class Meta:
        model = File
        fields = (
            "id", "name", "owner", "folder", "folder_name",
            "size", "mime_type", "created_at"
        )
        

class SharedLinkCreateSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = SharedLink
        fields = ("id", "permission", "expires_at", "shared_with", "token")
        read_only_fields = ("id", "token")

    def validate_shared_with(self, value):
        """A user should not be able to share a file with themselves."""
        if value and value == self.context["request"].user:
            raise serializers.ValidationError(
                "You cannot share a file with yourself."
            )
        return value

    def validate_expires_at(self, value):
        """Expiry must be a future date."""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "Expiry date must be in the future."
            )
        return value


class SharedLinkSerializer(serializers.ModelSerializer):
    shared_with = serializers.StringRelatedField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = SharedLink
        fields = (
            "id", "token", "url", "permission",
            "expires_at", "shared_with", "created_by", "created_at"
        )

    def get_url(self, obj):
        request = self.context.get("request")
        path = f"/api/shared/{obj.token}/"
        if request:
            return request.build_absolute_uri(path)
        return path