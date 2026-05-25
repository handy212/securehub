from rest_framework import serializers

from .asset_models import (
    GuardAssetDepot,
    GuardAssetMaintenanceLog,
    GuardAssetStock,
    GuardAssetType,
    GuardAssetUnit,
    GuardingAssetPolicy,
    PostAssetKit,
    PostAssetKitLine,
    ShiftAssetManifest,
    ShiftAssetManifestLine,
)


class GuardAssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardAssetType
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class GuardAssetDepotSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = GuardAssetDepot
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class GuardAssetUnitSerializer(serializers.ModelSerializer):
    asset_type_name = serializers.CharField(source="asset_type.name", read_only=True)
    depot_name = serializers.CharField(source="depot.name", read_only=True)

    class Meta:
        model = GuardAssetUnit
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class GuardAssetStockSerializer(serializers.ModelSerializer):
    quantity_available = serializers.IntegerField(read_only=True)
    asset_type_name = serializers.CharField(source="asset_type.name", read_only=True)
    depot_name = serializers.CharField(source="depot.name", read_only=True)

    class Meta:
        model = GuardAssetStock
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class GuardAssetMaintenanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardAssetMaintenanceLog
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class GuardingAssetPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardingAssetPolicy
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class PostAssetKitLineSerializer(serializers.ModelSerializer):
    asset_type_name = serializers.CharField(source="asset_type.name", read_only=True)
    asset_type_code = serializers.CharField(source="asset_type.code", read_only=True)
    tracking_mode = serializers.CharField(source="asset_type.tracking_mode", read_only=True)

    class Meta:
        model = PostAssetKitLine
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class PostAssetKitSerializer(serializers.ModelSerializer):
    lines = PostAssetKitLineSerializer(many=True, read_only=True)
    post_name = serializers.CharField(source="post.name", read_only=True)

    class Meta:
        model = PostAssetKit
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ShiftAssetManifestLineSerializer(serializers.ModelSerializer):
    asset_type_name = serializers.CharField(source="asset_type.name", read_only=True)
    asset_type_code = serializers.CharField(source="asset_type.code", read_only=True)
    tracking_mode = serializers.CharField(source="asset_type.tracking_mode", read_only=True)
    asset_tag = serializers.CharField(source="asset_unit.asset_tag", read_only=True, allow_null=True)

    class Meta:
        model = ShiftAssetManifestLine
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ShiftAssetManifestSerializer(serializers.ModelSerializer):
    lines = ShiftAssetManifestLineSerializer(many=True, read_only=True)
    guard_name = serializers.CharField(source="assignment.guard.full_name", read_only=True)
    shift_label = serializers.SerializerMethodField()

    class Meta:
        model = ShiftAssetManifest
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def get_shift_label(self, obj):
        shift = obj.assignment.shift
        return f"{shift.post.name} {shift.starts_at:%Y-%m-%d %H:%M}"


class IssueManifestLineSerializer(serializers.Serializer):
    line_id = serializers.UUIDField()
    asset_unit_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, default=1, required=False)
    condition_out = serializers.CharField(required=False, allow_blank=True, default="")
    depot_id = serializers.UUIDField(required=False, allow_null=True)


class ReturnManifestLineSerializer(serializers.Serializer):
    line_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    condition_in = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=ShiftAssetManifestLine.Status.choices,
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AssetOverrideSerializer(serializers.Serializer):
    phase = serializers.ChoiceField(choices=["clock_in", "clock_out"])
    reason = serializers.CharField(min_length=3, max_length=500)
