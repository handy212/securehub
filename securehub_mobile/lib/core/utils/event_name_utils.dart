String friendlyEventName(String? raw, {String fallback = 'System Event'}) {
  final value = (raw ?? '').trim();
  if (value.isEmpty) return fallback;

  final normalized = value
      .replaceAll(RegExp(r'[_-]+'), ' ')
      .replaceAllMapped(RegExp(r'(?<=[a-z])(?=[A-Z])'), (_) => ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
  final key = normalized.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '');

  if (key.contains('magneticzoneinstantalarm')) {
    return 'Door/Window Alarm';
  }
  if (key.contains('mobilezoneinstantalarm') ||
      key.contains('instantzonealarm') ||
      key.contains('zoneinstantalarm')) {
    return 'Zone Alarm';
  }
  if (key.contains('alarmtrg') ||
      key.contains('alarmreport') ||
      key.contains('alarmtriggered')) {
    return 'Alarm Triggered';
  }
  if (key.contains('alarmrest') || key.contains('alarmrestored')) {
    return 'Alarm Restored';
  }
  if (key.contains('snapshot')) return 'Snapshot Captured';
  if (key.contains('linkage')) return 'Footage';
  if (key.contains('armaway') || key.contains('awayarmed')) {
    return 'Away Armed';
  }
  if (key.contains('stayarm') || key.contains('stayarmed')) {
    return 'Stay Armed';
  }
  if (key.contains('disarm')) return 'Disarmed';
  if (key.contains('lowbattery')) return 'Low Battery';
  if (key.contains('tamper')) return 'Tamper Detected';
  if (key.contains('vmd') || key.contains('motion')) return 'Motion Detected';
  if (key.contains('silence')) return 'Silence Alarm';

  return normalized
      .split(' ')
      .where((part) => part.isNotEmpty)
      .map((part) => part[0].toUpperCase() + part.substring(1).toLowerCase())
      .join(' ');
}

String? eventPayloadString(Map<String, dynamic> data, List<String> keys) {
  for (final key in keys) {
    final value = data[key]?.toString().trim();
    if (value != null && value.isNotEmpty) return value;
  }
  return null;
}

String eventPayloadSearchText(Map<String, dynamic> data) {
  final parts = <String>[];

  void add(dynamic value) {
    final text = value?.toString().trim();
    if (text != null && text.isNotEmpty) parts.add(text);
  }

  for (final key in const [
    'type',
    'event_type',
    'eventType',
    'event_title',
    'eventTitle',
    'event_name',
    'eventName',
    'normalized_event_type',
    'normalizedEventType',
    'raw_event_type',
    'rawEventType',
    'severity',
  ]) {
    add(data[key]);
  }

  final alarmData = data['alarmData'] ?? data['alarm_data'];
  if (alarmData is Map) {
    add(alarmData['eventType']);
    add(alarmData['eventDescription']);
    final cidEvent = alarmData['CIDEvent'] ?? alarmData['cidEvent'];
    if (cidEvent is Map) {
      add(cidEvent['description']);
      add(cidEvent['code']);
      add(cidEvent['evttype']);
    }
  }

  return parts.join(' ').toLowerCase();
}
