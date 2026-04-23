// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'site.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ZoneImpl _$$ZoneImplFromJson(Map<String, dynamic> json) => _$ZoneImpl(
  id: json['id'] as String? ?? '',
  name: json['name'] as String? ?? '',
  zoneNumber: (json['zoneNumber'] as num?)?.toInt() ?? 0,
  state: json['state'] as String? ?? 'normal',
  lowBattery: json['lowBattery'] as bool? ?? false,
  tamper: json['tamper'] as bool? ?? false,
  signalStrength: json['signalStrength'] as String? ?? '',
  isOnline: json['isOnline'] as bool? ?? true,
  deviceNumber: (json['deviceNumber'] as num?)?.toInt() ?? 0,
  detectorType: json['detectorType'] as String? ?? '',
  deviceType: json['deviceType'] as String? ?? '',
  chargeValue: (json['chargeValue'] as num?)?.toInt() ?? 0,
  displayType: json['displayType'] as String? ?? '',
  iconType: json['iconType'] as String? ?? '',
  firmwareVersion: json['firmwareVersion'] as String? ?? '',
  hardwareVersion: json['hardwareVersion'] as String? ?? '',
  modelNumber: json['modelNumber'] as String? ?? '',
);

Map<String, dynamic> _$$ZoneImplToJson(_$ZoneImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'zoneNumber': instance.zoneNumber,
      'state': instance.state,
      'lowBattery': instance.lowBattery,
      'tamper': instance.tamper,
      'signalStrength': instance.signalStrength,
      'isOnline': instance.isOnline,
      'deviceNumber': instance.deviceNumber,
      'detectorType': instance.detectorType,
      'deviceType': instance.deviceType,
      'chargeValue': instance.chargeValue,
      'displayType': instance.displayType,
      'iconType': instance.iconType,
      'firmwareVersion': instance.firmwareVersion,
      'hardwareVersion': instance.hardwareVersion,
      'modelNumber': instance.modelNumber,
    };

_$SubsystemImpl _$$SubsystemImplFromJson(Map<String, dynamic> json) =>
    _$SubsystemImpl(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      hikSubsystemId: json['hikSubsystemId'] as String? ?? '',
      subsystemNumber: (json['subsystemNumber'] as num?)?.toInt() ?? 0,
      status: json['status'] as String? ?? 'disarmed',
      zones:
          (json['zones'] as List<dynamic>?)
              ?.map((e) => Zone.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$$SubsystemImplToJson(_$SubsystemImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'hikSubsystemId': instance.hikSubsystemId,
      'subsystemNumber': instance.subsystemNumber,
      'status': instance.status,
      'zones': instance.zones,
    };

_$AlarmPanelDeviceImpl _$$AlarmPanelDeviceImplFromJson(
  Map<String, dynamic> json,
) => _$AlarmPanelDeviceImpl(
  id: json['id'] as String? ?? '',
  site: json['site'] as String? ?? '',
  name: json['name'] as String? ?? '',
  serialNumber: json['serialNumber'] as String? ?? '',
  hikDeviceId: json['hikDeviceId'] as String? ?? '',
  deviceType: json['deviceType'] as String? ?? 'panel',
  isOnline: json['isOnline'] as bool? ?? true,
  firmwareVersion: json['firmwareVersion'] as String? ?? '',
  hardwareVersion: json['hardwareVersion'] as String? ?? '',
  modelNumber: json['modelNumber'] as String? ?? '',
  lastSeen: json['last_seen'] == null
      ? null
      : DateTime.parse(json['last_seen'] as String),
  subsystems:
      (json['subsystems'] as List<dynamic>?)
          ?.map((e) => Subsystem.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
);

Map<String, dynamic> _$$AlarmPanelDeviceImplToJson(
  _$AlarmPanelDeviceImpl instance,
) => <String, dynamic>{
  'id': instance.id,
  'site': instance.site,
  'name': instance.name,
  'serialNumber': instance.serialNumber,
  'hikDeviceId': instance.hikDeviceId,
  'deviceType': instance.deviceType,
  'isOnline': instance.isOnline,
  'firmwareVersion': instance.firmwareVersion,
  'hardwareVersion': instance.hardwareVersion,
  'modelNumber': instance.modelNumber,
  'last_seen': instance.lastSeen?.toIso8601String(),
  'subsystems': instance.subsystems,
};

_$VideoChannelImpl _$$VideoChannelImplFromJson(Map<String, dynamic> json) =>
    _$VideoChannelImpl(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      hikChannelId: json['hikChannelId'] as String? ?? '',
      channelNumber: (json['channelNumber'] as num?)?.toInt() ?? 0,
      isOnline: json['isOnline'] as bool? ?? true,
    );

Map<String, dynamic> _$$VideoChannelImplToJson(_$VideoChannelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'hikChannelId': instance.hikChannelId,
      'channelNumber': instance.channelNumber,
      'isOnline': instance.isOnline,
    };

_$VideoDeviceImpl _$$VideoDeviceImplFromJson(Map<String, dynamic> json) =>
    _$VideoDeviceImpl(
      id: json['id'] as String? ?? '',
      site: json['site'] as String? ?? '',
      name: json['name'] as String? ?? '',
      serialNumber: json['serialNumber'] as String? ?? '',
      hikDeviceId: json['hikDeviceId'] as String? ?? '',
      deviceType: json['deviceType'] as String? ?? 'nvr',
      isOnline: json['isOnline'] as bool? ?? true,
      firmwareVersion: json['firmwareVersion'] as String? ?? '',
      hardwareVersion: json['hardwareVersion'] as String? ?? '',
      modelNumber: json['modelNumber'] as String? ?? '',
      lastSeen: json['last_seen'] == null
          ? null
          : DateTime.parse(json['last_seen'] as String),
      channels:
          (json['channels'] as List<dynamic>?)
              ?.map((e) => VideoChannel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$$VideoDeviceImplToJson(_$VideoDeviceImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'site': instance.site,
      'name': instance.name,
      'serialNumber': instance.serialNumber,
      'hikDeviceId': instance.hikDeviceId,
      'deviceType': instance.deviceType,
      'isOnline': instance.isOnline,
      'firmwareVersion': instance.firmwareVersion,
      'hardwareVersion': instance.hardwareVersion,
      'modelNumber': instance.modelNumber,
      'last_seen': instance.lastSeen?.toIso8601String(),
      'channels': instance.channels,
    };

_$SiteImpl _$$SiteImplFromJson(Map<String, dynamic> json) => _$SiteImpl(
  id: json['id'] as String? ?? '',
  name: json['name'] as String? ?? '',
  address: json['address'] as String? ?? '',
  city: json['city'] as String? ?? '',
  country: json['country'] as String? ?? '',
  hikSiteId: json['hikSiteId'] as String? ?? '',
  timezone: json['timezone'] as String? ?? 'UTC',
  isActive: json['isActive'] as bool? ?? true,
  canControlAlarm: json['can_control_alarm'] as bool? ?? false,
  devices:
      (json['devices'] as List<dynamic>?)
          ?.map((e) => AlarmPanelDevice.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  videoDevices:
      (json['video_devices'] as List<dynamic>?)
          ?.map((e) => VideoDevice.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  subsystems:
      (json['subsystems'] as List<dynamic>?)
          ?.map((e) => Subsystem.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
);

Map<String, dynamic> _$$SiteImplToJson(_$SiteImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'address': instance.address,
      'city': instance.city,
      'country': instance.country,
      'hikSiteId': instance.hikSiteId,
      'timezone': instance.timezone,
      'isActive': instance.isActive,
      'can_control_alarm': instance.canControlAlarm,
      'devices': instance.devices,
      'video_devices': instance.videoDevices,
      'subsystems': instance.subsystems,
    };

_$PaginatedSitesImpl _$$PaginatedSitesImplFromJson(Map<String, dynamic> json) =>
    _$PaginatedSitesImpl(
      count: (json['count'] as num).toInt(),
      next: json['next'] as String?,
      previous: json['previous'] as String?,
      results: (json['results'] as List<dynamic>)
          .map((e) => Site.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$$PaginatedSitesImplToJson(
  _$PaginatedSitesImpl instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
