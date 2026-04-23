// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'alarm_event.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$AlarmEventImpl _$$AlarmEventImplFromJson(Map<String, dynamic> json) =>
    _$AlarmEventImpl(
      id: json['id'] as String? ?? '',
      eventType: json['event_type'] as String? ?? '',
      eventCategory: json['event_category'] as String? ?? 'info',
      severity: json['severity'] as String? ?? 'low',
      occurredAt: json['occurred_at'] as String? ?? '',
      siteName: json['site_name'] as String? ?? '',
      subsystem: json['subsystem'] as String?,
      subsystemName: json['subsystem_name'] as String?,
      zone: json['zone'] as String?,
      zoneName: json['zone_name'] as String?,
      zoneNumber: (json['zone_number'] as num?)?.toInt(),
      zoneDetectorType: json['zone_detector_type'] as String?,
      hasMedia: json['has_media'] as bool? ?? false,
      acknowledged: json['acknowledged'] as bool? ?? false,
      acknowledgedAt: json['acknowledged_at'] as String?,
      performedBy: json['performed_by'] as String?,
      payload: json['payload'] as Map<String, dynamic>? ?? const {},
    );

Map<String, dynamic> _$$AlarmEventImplToJson(_$AlarmEventImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'event_type': instance.eventType,
      'event_category': instance.eventCategory,
      'severity': instance.severity,
      'occurred_at': instance.occurredAt,
      'site_name': instance.siteName,
      'subsystem': instance.subsystem,
      'subsystem_name': instance.subsystemName,
      'zone': instance.zone,
      'zone_name': instance.zoneName,
      'zone_number': instance.zoneNumber,
      'zone_detector_type': instance.zoneDetectorType,
      'has_media': instance.hasMedia,
      'acknowledged': instance.acknowledged,
      'acknowledged_at': instance.acknowledgedAt,
      'performed_by': instance.performedBy,
      'payload': instance.payload,
    };

_$AlarmPictureImpl _$$AlarmPictureImplFromJson(Map<String, dynamic> json) =>
    _$AlarmPictureImpl(
      url: json['url'] as String? ?? '',
      encrypt: json['encrypt'] as bool? ?? false,
      type: json['type'] as String? ?? 'image',
      id: json['id'] as String?,
    );

Map<String, dynamic> _$$AlarmPictureImplToJson(_$AlarmPictureImpl instance) =>
    <String, dynamic>{
      'url': instance.url,
      'encrypt': instance.encrypt,
      'type': instance.type,
      'id': instance.id,
    };

_$PaginatedEventsImpl _$$PaginatedEventsImplFromJson(
  Map<String, dynamic> json,
) => _$PaginatedEventsImpl(
  count: (json['count'] as num?)?.toInt() ?? 0,
  next: json['next'] as String?,
  previous: json['previous'] as String?,
  results:
      (json['results'] as List<dynamic>?)
          ?.map((e) => AlarmEvent.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
);

Map<String, dynamic> _$$PaginatedEventsImplToJson(
  _$PaginatedEventsImpl instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
