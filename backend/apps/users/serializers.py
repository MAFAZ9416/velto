"""
Serializers for Authentication, User Profile, Password Reset, and Verification.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserRegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration (POST /api/v1/auth/register/).
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value: str) -> str:
        clean_email = value.strip().lower()
        if User.objects.filter(email__iexact=clean_email).exists() or User.objects.filter(username__iexact=clean_email).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return clean_email

    def validate_password(self, value: str) -> str:
        email = self.initial_data.get("email", "")
        dummy_user = User(email=email, username=email)
        validate_password(value, user=dummy_user)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
        )
        return user


class UserSummarySerializer(serializers.ModelSerializer):
    """
    Safe public user summary representation.
    """
    user_id = serializers.CharField(source="id", read_only=True)
    is_email_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["user_id", "email", "is_email_verified", "date_joined"]
        read_only_fields = fields

    def get_is_email_verified(self, obj) -> bool:
        profile = getattr(obj, "profile", None)
        return profile.is_email_verified if profile else False


class UserProfileDetailSerializer(serializers.Serializer):
    """
    Detailed user account and usage information for GET /api/v1/auth/me/.
    """
    user_id = serializers.CharField()
    email = serializers.EmailField()
    is_email_verified = serializers.BooleanField()
    account_status = serializers.CharField(default="active")
    storage_limit_bytes = serializers.IntegerField()
    storage_used_bytes = serializers.IntegerField()
    daily_conversion_count = serializers.IntegerField()
    daily_conversion_limit = serializers.IntegerField()
    monthly_conversion_count = serializers.IntegerField()
    monthly_conversion_limit = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSummarySerializer()


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value: str) -> str:
        email = self.initial_data.get("email", "")
        dummy_user = User(email=email, username=email)
        validate_password(value, user=dummy_user)
        return value


class EmailVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)


class EmailVerificationConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    token = serializers.CharField(required=True)


class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True)
