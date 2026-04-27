import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:intl/intl.dart';

import '../utils/event_name_utils.dart';

part 'alarm_event.freezed.dart';
part 'alarm_event.g.dart';

@Freezed(fromJson: true)
class AlarmEvent with _$AlarmEvent {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory AlarmEvent({
    @Default('') String id,
    @Default('') String eventType,
    // Classification fields added in backend migration 0004
    @Default('info') String eventCategory,
    @Default('low') String severity,
    @Default('') String occurredAt,
    @Default('') String siteName,
    String? subsystem,
    String? subsystemName,
    String? zone,
    String? zoneName,
    int? zoneNumber,
    String? zoneDetectorType,
    @Default(false) bool hasMedia,
    // Acknowledgement state
    @Default(false) bool acknowledged,
    String? acknowledgedAt,
    String? performedBy,
    @Default({}) Map<String, dynamic> payload,
  }) = _AlarmEvent;

  factory AlarmEvent.fromJson(Map<String, dynamic> json) =>
      _$AlarmEventFromJson(json);
}

extension AlarmEventX on AlarmEvent {
  Map<String, dynamic>? get _payloadAlarmData {
    final alarmData = payload['alarmData'] ?? payload['alarm_data'];
    if (alarmData is Map<String, dynamic>) {
      return alarmData;
    }
    if (alarmData is Map) {
      try {
        return Map<String, dynamic>.from(alarmData);
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  Map<String, dynamic>? get _payloadCidEvent {
    final cidEvent =
        _payloadAlarmData?['CIDEvent'] ?? _payloadAlarmData?['cidEvent'];
    if (cidEvent is Map<String, dynamic>) {
      return cidEvent;
    }
    if (cidEvent is Map) {
      try {
        return Map<String, dynamic>.from(cidEvent);
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  String? get resolvedZoneName {
    if (zoneName != null && zoneName!.trim().isNotEmpty) {
      return zoneName!.trim();
    }
    final cidZoneName = _payloadCidEvent?['zoneName']?.toString().trim();
    if (cidZoneName != null && cidZoneName.isNotEmpty) {
      return cidZoneName;
    }
    return null;
  }

  String? get resolvedSubsystemName {
    if (subsystemName != null && subsystemName!.trim().isNotEmpty) {
      return subsystemName!.trim();
    }
    final systemName = _payloadCidEvent?['systemName']?.toString().trim();
    if (systemName != null && systemName.isNotEmpty) {
      return systemName;
    }
    return null;
  }

  int? get resolvedZoneNumber {
    if (zoneNumber != null) return zoneNumber;
    final cidZoneNumber = _payloadCidEvent?['zone'];
    if (cidZoneNumber is num) return cidZoneNumber.toInt();
    return int.tryParse(cidZoneNumber?.toString() ?? '');
  }

  String get alertHeadline {
    final zone = resolvedZoneName;
    final title = displayTitle;
    if (zone == null || zone.isEmpty) {
      return title;
    }
    final lowerTitle = title.toLowerCase();
    final lowerZone = zone.toLowerCase();
    if (lowerTitle.contains(lowerZone)) {
      return title;
    }
    if (lowerTitle == 'motion detected') {
      return '$zone Motion';
    }
    if (lowerTitle == 'door/window alarm' ||
        lowerTitle == 'zone alarm' ||
        lowerTitle == 'alarm triggered') {
      return zone;
    }
    return '$zone $title';
  }

  String get activityTitle {
    final title = displayTitle;
    final zone = resolvedZoneName;
    if (zone == null || zone.isEmpty) {
      return title;
    }

    final lowerTitle = title.toLowerCase();
    if (lowerTitle == 'zone alarm' ||
        lowerTitle == 'door/window alarm' ||
        lowerTitle == 'alarm triggered') {
      return zone;
    }
    return title;
  }

  String get normalizedEventType {
    final normalized = payload['normalized_event_type']?.toString().trim();
    if (normalized != null && normalized.isNotEmpty) {
      return normalized;
    }
    return eventType;
  }

  String get displayTitle {
    final payloadName = payload['event_name']?.toString().trim();
    if (payloadName != null && payloadName.isNotEmpty) {
      return friendlyEventName(payloadName);
    }

    final cidEvent = _payloadCidEvent;
    if (cidEvent != null) {
      final description = cidEvent['description']?.toString().trim();
      if (description != null && description.isNotEmpty) {
        return friendlyEventName(description);
      }
    }

    final type = eventType.toUpperCase();
    String title = switch (type) {
      'ALARMTRG' || 'ALARM' || 'ALARM_REPORT' => 'Alarm Triggered',
      'ALARMREST' => 'Alarm Restored',
      'LINKAGE' => 'Footage',
      'ARMAWAY' || 'ARM' || 'AWAY_ARM' => 'Away Armed',
      'DISARM' => 'Disarmed',
      'STAYARM' || 'STAY' || 'STAY_ARM' => 'Stay Armed',
      'LOWBATTERY' || 'LOW_BATTERY' => 'Low Battery',
      'TAMPER' => 'Tamper Detected',
      'VMD' => 'Motion Detected',
      'SILENCE' || 'SILENCE_ALARM' => 'Silence Alarm',
      _ =>
        type
            .replaceAll(RegExp(r'[^a-zA-Z0-9]'), ' ')
            .split(' ')
            .map(
              (s) => s.isNotEmpty
                  ? s[0].toUpperCase() + s.substring(1).toLowerCase()
                  : '',
            )
            .join(' ')
            .trim(),
    };

    // Clean up title if it contains redundant information from subsystem/area or zone
    String cleanTitle = title;
    final List<String> redundantParts = [
      if (subsystemName != null && subsystemName!.isNotEmpty)
        subsystemName!.toLowerCase(),
      if (zoneName != null && zoneName!.isNotEmpty) zoneName!.toLowerCase(),
    ];

    for (final part in redundantParts) {
      final lowTitle = cleanTitle.toLowerCase();
      if (lowTitle.contains(part)) {
        // Try to remove the part and common separators
        final regex = RegExp(
          '\\b${RegExp.escape(part)}'
          r'\b\s*[:\-\(\)]*\s*|[:\-\(\)]*\s*\b'
          '${RegExp.escape(part)}'
          r'\b',
          caseSensitive: false,
        );
        cleanTitle = cleanTitle.replaceAll(regex, '').trim();
      }
    }

    // Capitalize first letter if we cleaned it up
    if (cleanTitle != title && cleanTitle.isNotEmpty) {
      cleanTitle = cleanTitle[0].toUpperCase() + cleanTitle.substring(1);
    }

    return friendlyEventName(
      cleanTitle.isEmpty
          ? (title.isEmpty ? 'System Event' : title)
          : cleanTitle,
    );
  }

  String get displaySubtitle {
    final parts = <String>[];

    try {
      if (occurredAt.isNotEmpty) {
        final dt = DateTime.tryParse(occurredAt)?.toLocal();
        if (dt != null) {
          parts.add(DateFormat('HH:mm').format(dt));
        }
      }
    } catch (_) {}

    if (siteName.isNotEmpty) {
      parts.add(siteName); // "Panel"
    }

    if (resolvedSubsystemName != null && resolvedSubsystemName!.isNotEmpty) {
      parts.add(resolvedSubsystemName!); // "Area"
    }

    return parts.join(' • ');
  }

  bool get isOperationEvent {
    final normalized = normalizedEventType.toLowerCase();
    if (eventCategory == 'arm') return true;

    return normalized.contains('arm') ||
        normalized.contains('disarm') ||
        normalized.contains('stay') ||
        normalized.contains('bypass');
  }

  bool get hasEffectiveMedia {
    if (hasMedia) return true;
    final data = payload;
    final pictures = data['pictures'];
    if (pictures is List && pictures.isNotEmpty) {
      return true;
    }
    // Check alarmData/alarm_data (common Hikvision PIR structure)
    final alarmData = _payloadAlarmData;
    if (alarmData is Map<String, dynamic>) {
      final list =
          alarmData['pictureList'] ??
          alarmData['picture_list'] ??
          alarmData['mediaList'];
      if (list is List && list.isNotEmpty) {
        return true;
      }
      if (alarmData.containsKey('url') || alarmData.containsKey('videoUrl')) {
        return true;
      }
    }
    // Check direct keys
    if (data.containsKey('url') ||
        data.containsKey('videoUrl') ||
        data.containsKey('media_path')) {
      return true;
    }
    return false;
  }

  String get fullLocation {
    final parts = <String>[];
    if (resolvedZoneName != null && resolvedZoneName!.isNotEmpty) {
      String zoneStr = resolvedZoneName!;
      if (resolvedZoneNumber != null) {
        zoneStr += ' (Z$resolvedZoneNumber)';
      }
      parts.add(zoneStr);
    }
    if (resolvedSubsystemName != null && resolvedSubsystemName!.isNotEmpty) {
      parts.add(resolvedSubsystemName!);
    }
    if (parts.isEmpty && siteName.isNotEmpty) {
      parts.add(siteName);
    }
    return parts.isEmpty ? 'System Event' : parts.join(' - ');
  }
}

@Freezed(fromJson: true)
class AlarmPicture with _$AlarmPicture {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory AlarmPicture({
    @Default('') String url,
    @Default(false) bool encrypt,
    @Default('image') String type,
    String? id,
  }) = _AlarmPicture;

  factory AlarmPicture.fromJson(Map<String, dynamic> json) =>
      _$AlarmPictureFromJson(json);
}

@Freezed(fromJson: true)
class PaginatedEvents with _$PaginatedEvents {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory PaginatedEvents({
    @Default(0) int count,
    String? next,
    String? previous,
    @Default([]) List<AlarmEvent> results,
  }) = _PaginatedEvents;

  factory PaginatedEvents.fromJson(Map<String, dynamic> json) =>
      _$PaginatedEventsFromJson(json);
}
