class SiteRuntimeSnapshot {
  const SiteRuntimeSnapshot({
    required this.siteId,
    required this.armedSubsystems,
    required this.disarmedSubsystems,
    required this.activeAlarmCount,
    required this.offlineDeviceCount,
    required this.peripherals,
    required this.outputs,
  });

  final String siteId;
  final int armedSubsystems;
  final int disarmedSubsystems;
  final int activeAlarmCount;
  final int offlineDeviceCount;
  final List<RuntimePeripheral> peripherals;
  final List<RuntimeOutput> outputs;

  factory SiteRuntimeSnapshot.fromJson(Map<String, dynamic> json) {
    final peripheralData = (_listValue(json['peripherals']) ?? const <dynamic>[])
        .whereType<Map>()
        .map((item) => RuntimePeripheral.fromJson(Map<String, dynamic>.from(item)))
        .toList();
    final outputData = (_listValue(json['outputs']) ?? const <dynamic>[])
        .whereType<Map>()
        .map((item) => RuntimeOutput.fromJson(Map<String, dynamic>.from(item)))
        .toList();

    return SiteRuntimeSnapshot(
      siteId: (json['siteId'] ?? json['site_id'] ?? '').toString(),
      armedSubsystems: _toInt(json['armedSubsystems'] ?? json['armed_subsystems']),
      disarmedSubsystems: _toInt(
        json['disarmedSubsystems'] ?? json['disarmed_subsystems'],
      ),
      activeAlarmCount: _toInt(
        json['activeAlarmCount'] ?? json['active_alarm_count'],
      ),
      offlineDeviceCount: _toInt(
        json['offlineDeviceCount'] ?? json['offline_device_count'],
      ),
      peripherals: peripheralData,
      outputs: outputData,
    );
  }
}

class RuntimePeripheral {
  const RuntimePeripheral({
    required this.id,
    required this.name,
    required this.type,
    required this.number,
    required this.serialNumber,
    required this.batteryStatus,
    required this.signalStrength,
    required this.tamper,
    required this.bypassed,
    required this.networkStatus,
    required this.isOnline,
  });

  final String id;
  final String name;
  final String type;
  final int number;
  final String serialNumber;
  final String batteryStatus;
  final String signalStrength;
  final bool tamper;
  final bool bypassed;
  final String networkStatus;
  final bool isOnline;

  factory RuntimePeripheral.fromJson(Map<String, dynamic> json) {
    return RuntimePeripheral(
      id: (json['id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      type: (json['type'] ?? json['peripheralType'] ?? '').toString(),
      number: _toInt(json['number'] ?? json['peripheralNumber']),
      serialNumber: (json['serialNumber'] ?? json['serial_number'] ?? '').toString(),
      batteryStatus: (json['batteryStatus'] ?? json['battery_status'] ?? '')
          .toString(),
      signalStrength: (json['signalStrength'] ?? json['signal_strength'] ?? '')
          .toString(),
      tamper: _toBool(json['tamper']),
      bypassed: _toBool(json['bypassed']),
      networkStatus: (json['networkStatus'] ?? json['network_status'] ?? '')
          .toString(),
      isOnline: _toBool(json['isOnline'] ?? json['is_online'], fallback: true),
    );
  }

  String get typeLabel {
    switch (type.toLowerCase()) {
      case 'keyfob':
        return 'Keyfob';
      case 'keypad':
        return 'Keypad';
      case 'card_reader':
      case 'reader':
        return 'Reader';
      case 'siren':
        return 'Siren';
      case 'repeater':
        return 'Repeater';
      case 'transmitter':
      case 'wireless_transmitter':
        return 'Transmitter';
      case 'output_module':
        return 'Output Module';
      default:
        return _humanize(type, fallback: 'Peripheral');
    }
  }

  String get statusLabel {
    if (!isOnline) return 'Offline';
    if (tamper) return 'Tamper';
    if (bypassed) return 'Bypassed';
    return 'Online';
  }
}

class RuntimeOutput {
  const RuntimeOutput({
    required this.id,
    required this.name,
    required this.number,
    required this.status,
    required this.batteryStatus,
    required this.signalStrength,
    required this.linkage,
    required this.scenarioTypes,
    required this.isOnline,
  });

  final String id;
  final String name;
  final int number;
  final String status;
  final String batteryStatus;
  final String signalStrength;
  final bool linkage;
  final List<String> scenarioTypes;
  final bool isOnline;

  factory RuntimeOutput.fromJson(Map<String, dynamic> json) {
    final rawScenarios = _listValue(json['scenarioTypes']) ??
        _listValue(json['scenario_types']) ??
        const <dynamic>[];
    final scenarios = rawScenarios.map((item) => item.toString()).toList();

    return RuntimeOutput(
      id: (json['id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      number: _toInt(json['number'] ?? json['outputNumber'] ?? json['output_number']),
      status: (json['status'] ?? '').toString(),
      batteryStatus: (json['batteryStatus'] ?? json['battery_status'] ?? '')
          .toString(),
      signalStrength: (json['signalStrength'] ?? json['signal_strength'] ?? '')
          .toString(),
      linkage: _toBool(json['linkage']),
      scenarioTypes: scenarios,
      isOnline: _toBool(json['isOnline'] ?? json['is_online'], fallback: true),
    );
  }

  String get statusLabel {
    if (!isOnline) return 'Offline';
    if (status.trim().isEmpty) return 'Ready';
    return _humanize(status, fallback: 'Ready');
  }
}

List<dynamic>? _listValue(dynamic value) {
  if (value is List<dynamic>) return value;
  if (value is List) return value.cast<dynamic>();
  return null;
}

int _toInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

bool _toBool(dynamic value, {bool fallback = false}) {
  if (value is bool) return value;
  final normalized = value?.toString().toLowerCase().trim();
  if (normalized == 'true' || normalized == '1' || normalized == 'yes') {
    return true;
  }
  if (normalized == 'false' || normalized == '0' || normalized == 'no') {
    return false;
  }
  return fallback;
}

String _humanize(String value, {required String fallback}) {
  final normalized = value.trim();
  if (normalized.isEmpty) return fallback;

  return normalized
      .replaceAll(RegExp(r'[_-]+'), ' ')
      .replaceAllMapped(
        RegExp(r'(?<=[a-z])(?=[A-Z])'),
        (_) => ' ',
      )
      .split(' ')
      .where((part) => part.isNotEmpty)
      .map(
        (part) => part[0].toUpperCase() + part.substring(1).toLowerCase(),
      )
      .join(' ');
}
