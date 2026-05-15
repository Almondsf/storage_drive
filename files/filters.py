import django_filters
from django.db.models import Q
from .models import File, Folder


class FileFilter(django_filters.FilterSet):

    # ?search=report
    # Searches across name AND mime_type using OR
    # icontains = case-insensitive contains
    search = django_filters.CharFilter(method="filter_search", label="Search")

    # ?mime_type=application/pdf
    # Exact match — client must send the full mime type string
    mime_type = django_filters.CharFilter(
        field_name="mime_type",
        lookup_expr="icontains",   # partial match so "pdf" matches "application/pdf"
        label="Mime type"
    )

    # ?folder=<uuid>
    # Filter files in a specific folder
    folder = django_filters.UUIDFilter(field_name="folder__id", label="Folder")

    # ?folder_null=true
    # Filter root-level files (no folder)
    folder_null = django_filters.BooleanFilter(
        field_name="folder",
        lookup_expr="isnull",
        label="Root level files only"
    )

    # ?created_after=2026-01-01
    # Files created on or after this date
    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",   # gte = greater than or equal to
        label="Created after"
    )

    # ?created_before=2026-12-31
    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",   # lte = less than or equal to
        label="Created before"
    )

    # ?min_size=1048576  (1MB in bytes)
    min_size = django_filters.NumberFilter(
        field_name="size",
        lookup_expr="gte",
        label="Minimum file size (bytes)"
    )

    # ?max_size=10485760  (10MB in bytes)
    max_size = django_filters.NumberFilter(
        field_name="size",
        lookup_expr="lte",
        label="Maximum file size (bytes)"
    )

    class Meta:
        model = File
        # Only these fields are filterable — explicit allowlist
        # Never use fields = "__all__" — exposes internal fields
        fields = [
            "search", "mime_type", "folder",
            "folder_null", "created_after", "created_before",
            "min_size", "max_size",
        ]

    def filter_search(self, queryset, name, value):
        
        return queryset.filter(
            Q(name__icontains=value) |
            Q(mime_type__icontains=value)
        )


class FolderFilter(django_filters.FilterSet):
    # ?search=documents
    search = django_filters.CharFilter(method="filter_search", label="Search")

    # ?parent=<uuid>
    parent = django_filters.UUIDFilter(field_name="parent__id", label="Parent folder")

    # ?parent_null=true — root folders only
    parent_null = django_filters.BooleanFilter(
        field_name="parent",
        lookup_expr="isnull",
        label="Root folders only"
    )

    # ?created_after=2026-01-01
    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte"
    )

    class Meta:
        model = Folder
        fields = ["search", "parent", "parent_null", "created_after"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)