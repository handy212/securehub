import 'package:geolocator/geolocator.dart';

class EmergencyStatus {
  const EmergencyStatus({
    required this.accountEnabled,
    required this.siteEnabled,
    required this.enabled,
  });

  final bool accountEnabled;
  final bool siteEnabled;
  final bool enabled;

  factory EmergencyStatus.fromJson(Map<String, dynamic> json) {
    return EmergencyStatus(
      accountEnabled: json['account_enabled'] == true,
      siteEnabled: json['site_enabled'] == true,
      enabled: json['enabled'] == true,
    );
  }
}

class EmergencyRequest {
  const EmergencyRequest({required this.id, required this.status, this.siteId});

  final String id;
  final String status;
  final String? siteId;

  bool get isActive =>
      status == 'open' ||
      status == 'acknowledged' ||
      status == 'dispatched' ||
      status == 'arrived';

  factory EmergencyRequest.fromJson(Map<String, dynamic> json) {
    return EmergencyRequest(
      id: json['id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'open',
      siteId: json['site']?.toString(),
    );
  }
}

class EmergencyPositionPayload {
  const EmergencyPositionPayload({
    required this.latitude,
    required this.longitude,
    this.accuracyM,
    this.altitudeM,
    this.speedMps,
    this.headingDeg,
    this.deviceTimestamp,
  });

  final double latitude;
  final double longitude;
  final double? accuracyM;
  final double? altitudeM;
  final double? speedMps;
  final double? headingDeg;
  final DateTime? deviceTimestamp;

  factory EmergencyPositionPayload.fromPosition(Position position) {
    return EmergencyPositionPayload(
      latitude: position.latitude,
      longitude: position.longitude,
      accuracyM: position.accuracy,
      altitudeM: position.altitude,
      speedMps: position.speed,
      headingDeg: position.heading,
      deviceTimestamp: position.timestamp,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'latitude': latitude.toStringAsFixed(9),
      'longitude': longitude.toStringAsFixed(9),
      if (accuracyM != null) 'accuracy_m': accuracyM!.toStringAsFixed(2),
      if (altitudeM != null) 'altitude_m': altitudeM!.toStringAsFixed(2),
      if (speedMps != null) 'speed_mps': speedMps!.toStringAsFixed(2),
      if (headingDeg != null) 'heading_deg': headingDeg!.toStringAsFixed(2),
      if (deviceTimestamp != null)
        'device_timestamp': deviceTimestamp!.toUtc().toIso8601String(),
    };
  }
}
