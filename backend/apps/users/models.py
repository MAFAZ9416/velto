"""
User Profile and Usage Models for VELTO Conversion.
"""

from datetime import date
from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    """
    Extends default User model with verification, tokens, per-user storage capacity,
    and conversion rate limits.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)

    password_reset_token = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    password_reset_sent_at = models.DateTimeField(blank=True, null=True)

    storage_limit_bytes = models.BigIntegerField(default=524_288_000)  # 500 MB default
    storage_used_bytes = models.BigIntegerField(default=0)

    daily_conversion_limit = models.IntegerField(default=50)
    monthly_conversion_limit = models.IntegerField(default=500)
    daily_conversion_count = models.IntegerField(default=0)
    monthly_conversion_count = models.IntegerField(default=0)
    last_conversion_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UserProfile({self.user.email})"

    def reset_usage_if_needed(self, today: date | None = None) -> None:
        """Reset daily or monthly conversion counters based on current UTC date."""
        today = today or timezone.now().date()
        update_fields = []

        if self.last_conversion_date is None:
            self.last_conversion_date = today
            self.daily_conversion_count = 0
            self.monthly_conversion_count = 0
            update_fields.extend(["last_conversion_date", "daily_conversion_count", "monthly_conversion_count"])
        else:
            if self.last_conversion_date != today:
                self.daily_conversion_count = 0
                update_fields.append("daily_conversion_count")
            if (self.last_conversion_date.year, self.last_conversion_date.month) != (today.year, today.month):
                self.monthly_conversion_count = 0
                update_fields.append("monthly_conversion_count")
            self.last_conversion_date = today
            update_fields.append("last_conversion_date")

        if update_fields:
            self.save(update_fields=list(set(update_fields)))

    def has_storage_capacity(self, file_size_bytes: int) -> bool:
        """Check if adding file_size_bytes would exceed storage_limit_bytes."""
        return (self.storage_used_bytes + max(0, file_size_bytes)) <= self.storage_limit_bytes

    def has_daily_capacity(self) -> bool:
        """Check if daily conversion count is within limits."""
        self.reset_usage_if_needed()
        return self.daily_conversion_count < self.daily_conversion_limit

    def has_monthly_capacity(self) -> bool:
        """Check if monthly conversion count is within limits."""
        self.reset_usage_if_needed()
        return self.monthly_conversion_count < self.monthly_conversion_limit

    def check_daily_limit(self) -> bool:
        """Alias helper checking daily conversion limit."""
        return self.has_daily_capacity()

    def check_monthly_limit(self) -> bool:
        """Alias helper checking monthly conversion limit."""
        return self.has_monthly_capacity()

    def check_storage_limit(self, file_size_bytes: int = 0) -> bool:
        """Alias helper checking storage limit."""
        return self.has_storage_capacity(file_size_bytes)

    def record_conversion_job(self, file_size_bytes: int) -> None:
        """Atomically increment storage used and conversion counters."""
        today = timezone.now().date()
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(pk=self.pk)
            profile.reset_usage_if_needed(today)
            profile.storage_used_bytes = F("storage_used_bytes") + max(0, file_size_bytes)
            profile.daily_conversion_count = F("daily_conversion_count") + 1
            profile.monthly_conversion_count = F("monthly_conversion_count") + 1
            profile.last_conversion_date = today
            profile.save(update_fields=[
                "storage_used_bytes",
                "daily_conversion_count",
                "monthly_conversion_count",
                "last_conversion_date",
            ])
            self.refresh_from_db()

    def add_storage_usage(self, file_size_bytes: int) -> None:
        """Add output or extra file bytes to user storage usage."""
        if file_size_bytes <= 0:
            return
        with transaction.atomic():
            UserProfile.objects.filter(pk=self.pk).update(
                storage_used_bytes=F("storage_used_bytes") + file_size_bytes
            )
            self.refresh_from_db()

    def release_storage(self, bytes_to_release: int) -> None:
        """Safely decrease storage used without dropping below 0."""
        if bytes_to_release <= 0:
            return
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(pk=self.pk)
            new_used = max(0, profile.storage_used_bytes - bytes_to_release)
            profile.storage_used_bytes = new_used
            profile.save(update_fields=["storage_used_bytes"])
            self.refresh_from_db()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Ensure UserProfile is automatically created for new users."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
