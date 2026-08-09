"""Recurring payment serializers."""

from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.recurring_payments.models import RecurringPayment
from apps.recurring_payments.services.recurring_service import RecurringPaymentService

User = get_user_model()


class RecurringPaymentSerializer(serializers.ModelSerializer):
    """Full recurring payment representation."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    receiver_email = serializers.EmailField(source="receiver.email", read_only=True)

    class Meta:
        model = RecurringPayment
        fields = [
            "id",
            "user_email",
            "receiver_email",
            "amount",
            "currency",
            "frequency",
            "start_date",
            "end_date",
            "next_payment_date",
            "last_payment_date",
            "status",
            "description",
            "failure_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_email",
            "next_payment_date",
            "last_payment_date",
            "failure_count",
            "created_at",
            "updated_at",
        ]


from decimal import Decimal

class CreateRecurringPaymentSerializer(serializers.Serializer):
    """Input for creating a new recurring payment."""

    receiver_email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    currency = serializers.CharField(max_length=3, default="INR", required=False)
    frequency = serializers.ChoiceField(choices=RecurringPayment.Frequency.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate_receiver_email(self, value: str) -> str:
        request = self.context.get("request")
        if request and value.lower() == request.user.email.lower():
            raise serializers.ValidationError("You cannot create a recurring payment to yourself.")
        try:
            User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError(f"No active user found with email '{value}'.")
        return value.lower()

    def validate_start_date(self, value: date) -> date:
        if value < date.today():
            raise serializers.ValidationError("Start date cannot be in the past.")
        return value

    def validate(self, attrs: dict) -> dict:
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        return attrs


class UpdateRecurringPaymentSerializer(serializers.ModelSerializer):
    """Allows partial updates to mutable fields."""

    class Meta:
        model = RecurringPayment
        fields = ["amount", "description", "end_date"]
