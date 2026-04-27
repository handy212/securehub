from rest_framework import serializers

from .models import AlarmOutput, AlarmPanelDevice, AlarmPeripheral, HikSiteDevice, Site, Subsystem, Zone
from .permissions import user_can_access_all_sites


class ZoneSerializer(serializers.ModelSerializer):
    zoneNumber = serializers.IntegerField(source='zone_number', read_only=True)
    deviceNumber = serializers.IntegerField(source='device_number', read_only=True, allow_null=True)
    deviceType = serializers.CharField(source='device_type', read_only=True)
    detectorType = serializers.CharField(source='detector_type', read_only=True)
    lowBattery = serializers.BooleanField(source='low_battery', read_only=True)
    signalStrength = serializers.CharField(source='signal_strength', read_only=True)
    isOnline = serializers.BooleanField(source='is_online', read_only=True)
    chargeValue = serializers.IntegerField(source='charge_value', read_only=True, allow_null=True)
    zoneType = serializers.CharField(source='zone_type', read_only=True)
    reason = serializers.CharField(read_only=True)
    healthStatus = serializers.CharField(source='health_status', read_only=True)
    modelNumber = serializers.CharField(source='model_number', read_only=True)
    accessModuleType = serializers.CharField(source='access_module_type', read_only=True)
    zoneAttribute = serializers.CharField(source='zone_attribute', read_only=True)
    shielded = serializers.BooleanField(read_only=True)
    magnetOpen = serializers.BooleanField(source='magnet_open', read_only=True, allow_null=True)
    networkStatus = serializers.CharField(source='network_status', read_only=True)
    displayType = serializers.ReadOnlyField(source='display_type')
    iconType = serializers.ReadOnlyField(source='icon_type')

    class Meta:
        model = Zone
        fields = (
            "id",
            "subsystem",
            "name",
            "zoneNumber",
            "deviceNumber",
            "deviceType",
            "detectorType",
            "state",
            "lowBattery",
            "tamper",
            "signalStrength",
            "isOnline",
            "chargeValue",
            "zoneType",
            "reason",
            "healthStatus",
            "modelNumber",
            "accessModuleType",
            "zoneAttribute",
            "shielded",
            "magnetOpen",
            "networkStatus",
            "displayType",
            "iconType",
        )


class AlarmPeripheralSerializer(serializers.ModelSerializer):
    peripheralType = serializers.CharField(source="peripheral_type", read_only=True)
    peripheralNumber = serializers.IntegerField(source="peripheral_number", read_only=True)
    serialNumber = serializers.CharField(source="serial_number", read_only=True)
    signalStrength = serializers.CharField(source="signal_strength", read_only=True)
    batteryStatus = serializers.CharField(source="battery_status", read_only=True)
    isOnline = serializers.BooleanField(source="is_online", read_only=True)
    lastOperationAt = serializers.DateTimeField(source="last_operation_at", read_only=True)
    lastTriggeredAt = serializers.DateTimeField(source="last_triggered_at", read_only=True)

    class Meta:
        model = AlarmPeripheral
        fields = (
            "id",
            "name",
            "peripheralType",
            "peripheralNumber",
            "serialNumber",
            "peripheral_type_label",
            "diagnostics_result",
            "network_status",
            "batteryStatus",
            "signalStrength",
            "tamper",
            "bypassed",
            "external_power",
            "isOnline",
            "last_seen_at",
            "lastOperationAt",
            "lastTriggeredAt",
            "metadata",
        )


class AlarmOutputSerializer(serializers.ModelSerializer):
    outputNumber = serializers.IntegerField(source="output_number", read_only=True)
    batteryStatus = serializers.CharField(source="battery_status", read_only=True)
    signalStrength = serializers.CharField(source="signal_strength", read_only=True)
    accessModuleType = serializers.CharField(source="access_module_type", read_only=True)
    relayAttribute = serializers.CharField(source="relay_attribute", read_only=True)
    subsystemNumbers = serializers.ListField(source="subsystem_numbers", read_only=True)
    scenarioTypes = serializers.ListField(source="scenario_types", read_only=True)
    isOnline = serializers.BooleanField(source="is_online", read_only=True)

    class Meta:
        model = AlarmOutput
        fields = (
            "id",
            "name",
            "outputNumber",
            "status",
            "tamper",
            "batteryStatus",
            "signalStrength",
            "linkage",
            "duration_const_output_enable",
            "is_available",
            "accessModuleType",
            "related_access_module_id",
            "module_address",
            "subsystemNumbers",
            "scenarioTypes",
            "relayAttribute",
            "device_number",
            "model_number",
            "diagnostics_result",
            "network_status",
            "isOnline",
            "serial_number",
        )


class SubsystemSerializer(serializers.ModelSerializer):
    hikSubsystemId = serializers.CharField(source='hik_subsystem_id', read_only=True)
    subsystemNumber = serializers.IntegerField(source='subsystem_number', read_only=True)
    panelIsOnline = serializers.BooleanField(source="device.is_online", read_only=True)
    zones = serializers.SerializerMethodField()

    def get_zones(self, obj):
        return ZoneSerializer(obj.zones.all(), many=True).data

    class Meta:
        model = Subsystem
        fields = (
            "id",
            "site",
            "device",
            "name",
            "hikSubsystemId",
            "subsystemNumber",
            "panelIsOnline",
            "status",
            "zones",
        )


class AlarmPanelDeviceSerializer(serializers.ModelSerializer):
    serialNumber = serializers.CharField(source='serial_number', read_only=True)
    hikDeviceId = serializers.CharField(source='hik_device_id', read_only=True)
    deviceType = serializers.CharField(source='device_type', read_only=True)
    isOnline = serializers.BooleanField(source='is_online', read_only=True)
    modelNumber = serializers.CharField(source='model_number', read_only=True)
    firmwareVersion = serializers.CharField(source='firmware_version', read_only=True)
    hardwareVersion = serializers.CharField(source='hardware_version', read_only=True)
    subsystems = SubsystemSerializer(many=True, read_only=True)
    peripherals = AlarmPeripheralSerializer(many=True, read_only=True)
    outputs = AlarmOutputSerializer(many=True, read_only=True)

    class Meta:
        model = AlarmPanelDevice
        fields = (
            "id",
            "site",
            "name",
            "serialNumber",
            "modelNumber",
            "firmwareVersion",
            "hardwareVersion",
            "hikDeviceId",
            "deviceType",
            "isOnline",
            "subsystems",
            "peripherals",
            "outputs",
        )


class HikSiteDeviceSerializer(serializers.ModelSerializer):
    hikDeviceId = serializers.CharField(source="hik_device_id", read_only=True)
    serialNumber = serializers.CharField(source="serial_number", read_only=True)
    deviceCategory = serializers.IntegerField(source="device_category", read_only=True, allow_null=True)
    deviceSubCategory = serializers.IntegerField(source="device_sub_category", read_only=True, allow_null=True)
    deviceType = serializers.CharField(source="device_type", read_only=True)
    deviceVersion = serializers.CharField(source="device_version", read_only=True)
    isOnline = serializers.BooleanField(source="is_online", read_only=True)
    isSubscribed = serializers.BooleanField(source="is_subscribed", read_only=True)

    class Meta:
        model = HikSiteDevice
        fields = (
            "id",
            "name",
            "hikDeviceId",
            "serialNumber",
            "deviceCategory",
            "deviceSubCategory",
            "deviceType",
            "deviceVersion",
            "isOnline",
            "isSubscribed",
        )


class SiteSerializer(serializers.ModelSerializer):
    devices = AlarmPanelDeviceSerializer(many=True, read_only=True)
    hikDevices = HikSiteDeviceSerializer(source="hik_devices", many=True, read_only=True)
    hikSiteId = serializers.CharField(source='hik_site_id', read_only=True)
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    can_control_alarm = serializers.SerializerMethodField()
    canControlAlarm = serializers.SerializerMethodField()

    class Meta:
        model = Site
        fields = (
            "id",
            "name",
            "address",
            "city",
            "state",
            "country",
            "primary_industry",
            "secondary_industry",
            "hikSiteId",
            "timezone",
            "isActive",
            "latitude",
            "longitude",
            "can_control_alarm",
            "canControlAlarm",
            "devices",
            "hikDevices",
        )

    def get_can_control_alarm(self, obj):
        return self._get_can_control_alarm(obj)

    def get_canControlAlarm(self, obj):
        return self._get_can_control_alarm(obj)

    def _get_can_control_alarm(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if user_can_access_all_sites(request.user):
            return True
        access = obj.access_list.filter(user=request.user).values_list(
            "can_control_alarm",
            flat=True,
        ).first()
        return bool(access)


class SiteStatusSerializer(serializers.Serializer):
    site_id = serializers.UUIDField()
    armed_subsystems = serializers.IntegerField()
    disarmed_subsystems = serializers.IntegerField()
    active_alarm_count = serializers.IntegerField()
    offline_device_count = serializers.IntegerField()
    subsystems = SubsystemSerializer(many=True)
