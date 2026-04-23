import 'package:freezed_annotation/freezed_annotation.dart';

part 'site.freezed.dart';
part 'site.g.dart';

// ---------------------------------------------------------------------------
// Zone
// ---------------------------------------------------------------------------

@Freezed(fromJson: true)
class Zone with _$Zone {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory Zone({
    @Default('') String id,
    @Default('') String name,
    @JsonKey(name: 'zoneNumber') @Default(0) int zoneNumber,
    @Default('normal') String state,
    @JsonKey(name: 'lowBattery') @Default(false) bool lowBattery,
    @Default(false) bool tamper,
    @JsonKey(name: 'signalStrength') @Default('') String signalStrength,
    @JsonKey(name: 'isOnline') @Default(true) bool isOnline,
    @JsonKey(name: 'deviceNumber') @Default(0) int? deviceNumber,
    @JsonKey(name: 'detectorType') @Default('') String detectorType,
    @JsonKey(name: 'deviceType') @Default('') String deviceType,
    @JsonKey(name: 'chargeValue') @Default(0) int? chargeValue,
    @JsonKey(name: 'displayType') @Default('') String displayType,
    @JsonKey(name: 'iconType') @Default('') String iconType,
    @JsonKey(name: 'firmwareVersion') @Default('') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') @Default('') String hardwareVersion,
    @JsonKey(name: 'modelNumber') @Default('') String modelNumber,
  }) = _Zone;

  factory Zone.fromJson(Map<String, dynamic> json) => _$ZoneFromJson(json);
}

// ---------------------------------------------------------------------------
// Subsystem (partition/area)
// ---------------------------------------------------------------------------

@Freezed(fromJson: true)
class Subsystem with _$Subsystem {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory Subsystem({
    @Default('') String id,
    @Default('') String name,
    @JsonKey(name: 'hikSubsystemId') @Default('') String hikSubsystemId,
    @JsonKey(name: 'subsystemNumber') @Default(0) int subsystemNumber,
    @Default('disarmed') String status,
    @Default([]) List<Zone> zones,
  }) = _Subsystem;

  factory Subsystem.fromJson(Map<String, dynamic> json) =>
      _$SubsystemFromJson(json);
}

// ---------------------------------------------------------------------------
// AlarmPanelDevice
// ---------------------------------------------------------------------------

@Freezed(fromJson: true)
class AlarmPanelDevice with _$AlarmPanelDevice {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory AlarmPanelDevice({
    @Default('') String id,
    @Default('') String site,
    @Default('') String name,
    @JsonKey(name: 'serialNumber') @Default('') String serialNumber,
    @JsonKey(name: 'hikDeviceId') @Default('') String hikDeviceId,
    @JsonKey(name: 'deviceType') @Default('panel') String deviceType,
    @JsonKey(name: 'isOnline') @Default(true) bool isOnline,
    @JsonKey(name: 'firmwareVersion') @Default('') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') @Default('') String hardwareVersion,
    @JsonKey(name: 'modelNumber') @Default('') String modelNumber,
    DateTime? lastSeen,
    @Default([]) List<Subsystem> subsystems,
  }) = _AlarmPanelDevice;

  factory AlarmPanelDevice.fromJson(Map<String, dynamic> json) =>
      _$AlarmPanelDeviceFromJson(json);
}

// ---------------------------------------------------------------------------
// VideoChannel / VideoDevice
// ---------------------------------------------------------------------------

@Freezed(fromJson: true)
class VideoChannel with _$VideoChannel {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory VideoChannel({
    @Default('') String id,
    @Default('') String name,
    @JsonKey(name: 'hikChannelId') @Default('') String hikChannelId,
    @JsonKey(name: 'channelNumber') @Default(0) int channelNumber,
    @JsonKey(name: 'isOnline') @Default(true) bool isOnline,
  }) = _VideoChannel;

  factory VideoChannel.fromJson(Map<String, dynamic> json) =>
      _$VideoChannelFromJson(json);
}

@Freezed(fromJson: true)
class VideoDevice with _$VideoDevice {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory VideoDevice({
    @Default('') String id,
    @Default('') String site,
    @Default('') String name,
    @JsonKey(name: 'serialNumber') @Default('') String serialNumber,
    @JsonKey(name: 'hikDeviceId') @Default('') String hikDeviceId,
    @JsonKey(name: 'deviceType') @Default('nvr') String deviceType,
    @JsonKey(name: 'isOnline') @Default(true) bool isOnline,
    @JsonKey(name: 'firmwareVersion') @Default('') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') @Default('') String hardwareVersion,
    @JsonKey(name: 'modelNumber') @Default('') String modelNumber,
    DateTime? lastSeen,
    @Default([]) List<VideoChannel> channels,
  }) = _VideoDevice;

  factory VideoDevice.fromJson(Map<String, dynamic> json) =>
      _$VideoDeviceFromJson(json);
}

// ---------------------------------------------------------------------------
// Site
// ---------------------------------------------------------------------------

@Freezed(fromJson: true)
class Site with _$Site {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory Site({
    @Default('') String id,
    @Default('') String name,
    @Default('') String address,
    @Default('') String city,
    @Default('') String country,
    @JsonKey(name: 'hikSiteId') @Default('') String hikSiteId,
    @Default('UTC') String timezone,
    @JsonKey(name: 'isActive') @Default(true) bool isActive,
    @Default(false) bool canControlAlarm,
    @Default([]) List<AlarmPanelDevice> devices,
    @Default([]) List<VideoDevice> videoDevices,
    @Default([]) List<Subsystem> subsystems,
  }) = _Site;

  factory Site.fromJson(Map<String, dynamic> json) => _$SiteFromJson(json);
}

@freezed
class PaginatedSites with _$PaginatedSites {
  const factory PaginatedSites({
    required int count,
    String? next,
    String? previous,
    required List<Site> results,
  }) = _PaginatedSites;

  factory PaginatedSites.fromJson(Map<String, dynamic> json) =>
      _$PaginatedSitesFromJson(json);
}
