from rest_framework import serializers
from .models import BroadcastMessage


class BroadcastMessageSerializer(serializers.ModelSerializer):
    view_count = serializers.IntegerField(source="views.count", read_only=True)
    is_viewed = serializers.SerializerMethodField()

    class Meta:
        model = BroadcastMessage
        fields = (
            "id",
            "title",
            "body",
            "message_type",
            "send_push",
            "send_email",
            "send_sms",
            "recipient",
            "sent_by",
            "status",
            "created_at",
            "sent_at",
            "view_count",
            "is_viewed",
        )
        read_only_fields = ("id", "sent_by", "status", "created_at", "sent_at", "view_count", "is_viewed")

    def get_is_viewed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.views.filter(user=request.user).exists()

    def create(self, validated_data):
        validated_data["sent_by"] = self.context["request"].user
        return super().create(validated_data)
