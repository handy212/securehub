// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'site_poll.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$LastEventImpl _$$LastEventImplFromJson(Map<String, dynamic> json) =>
    _$LastEventImpl(
      id: json['id'] as String?,
      type: json['type'] as String?,
      occurredAt: json['occurred_at'] as String?,
    );

Map<String, dynamic> _$$LastEventImplToJson(_$LastEventImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'type': instance.type,
      'occurred_at': instance.occurredAt,
    };

_$SitePollImpl _$$SitePollImplFromJson(Map<String, dynamic> json) =>
    _$SitePollImpl(
      siteId: json['site_id'] as String? ?? '',
      armedSubsystems: (json['armed_subsystems'] as num?)?.toInt() ?? 0,
      disarmedSubsystems: (json['disarmed_subsystems'] as num?)?.toInt() ?? 0,
      activeAlarmCount: (json['active_alarm_count'] as num?)?.toInt() ?? 0,
      offlineDeviceCount: (json['offline_device_count'] as num?)?.toInt() ?? 0,
      lastEvent: json['last_event'] == null
          ? null
          : LastEvent.fromJson(json['last_event'] as Map<String, dynamic>),
      subsystems:
          (json['subsystems'] as List<dynamic>?)
              ?.map((e) => Subsystem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$$SitePollImplToJson(_$SitePollImpl instance) =>
    <String, dynamic>{
      'site_id': instance.siteId,
      'armed_subsystems': instance.armedSubsystems,
      'disarmed_subsystems': instance.disarmedSubsystems,
      'active_alarm_count': instance.activeAlarmCount,
      'offline_device_count': instance.offlineDeviceCount,
      'last_event': instance.lastEvent,
      'subsystems': instance.subsystems,
    };
