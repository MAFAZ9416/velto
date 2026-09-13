from django.contrib import admin
from apps.conversions.models import ConversionJob


@admin.register(ConversionJob)
class ConversionJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "source_format",
        "target_format",
        "status",
        "original_filename",
        "output_filename",
        "file_size_bytes",
        "output_size_bytes",
        "user",
        "session_key",
        "created_at",
        "completed_at",
    ]
    list_filter = ["status", "source_format", "target_format"]
    search_fields = ["original_filename", "output_filename", "session_key", "error_message"]
    readonly_fields = [
        "id",
        "created_at",
        "started_at",
        "completed_at",
        "session_key",
        "file_size_bytes",
        "output_size_bytes",
        "input_path",
        "output_path",
    ]
    fieldsets = [
        ("Job", {"fields": ["id", "user", "session_key", "status"]}),
        ("Formats", {"fields": ["source_format", "target_format"]}),
        ("Input", {"fields": ["original_filename", "file_size_bytes", "input_path"]}),
        ("Output", {"fields": ["output_filename", "output_size_bytes", "output_path"]}),
        ("Timestamps", {"fields": ["created_at", "started_at", "completed_at"]}),
        ("Error", {"fields": ["error_message"]}),
    ]
    ordering = ["-created_at"]
