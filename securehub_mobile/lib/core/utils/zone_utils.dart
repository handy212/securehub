import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class ZoneUtils {
  static String getDeviceImage(String? detectorType, String name) {
    final type = (detectorType ?? '').toLowerCase();
    final n = name.toLowerCase();

    // 1. Exact matches for the assets we have
    if (type.contains('nvr')) return 'assets/devices/nvr.png';
    if (type.contains('panel') || type.contains('hub')) return 'assets/devices/axpro.png';
    
    if (type.contains('dualtech')) return 'assets/devices/DualTech.png';
    if (type.contains('triplepir')) return 'assets/devices/TriplePIR.png';
    if (type.contains('wallswitch')) return 'assets/devices/wallswitch.png';
    
    if (type.contains('campir') || type.contains('pir-cam')) return 'assets/devices/WirelessPIR-CAM.png';
    if (type.contains('pir')) return 'assets/devices/WirelessPIR.png';
    
    if (type.contains('externalsiren')) return 'assets/devices/ExternalSiren.png';
    if (type.contains('internalsiren')) return 'assets/devices/InternalSiren.png';
    if (type.contains('smoke')) return 'assets/devices/WirelessSmoke.png';
    if (type.contains('keyfob')) return 'assets/devices/WirelessKeyfob.png';
    if (type.contains('keypad')) return 'assets/devices/WirelessKeypad.png';
    if (type.contains('reader') || type.contains('card')) return 'assets/devices/WirelessKeypad.png';
    if (type.contains('panic') || type.contains('emergency')) return 'assets/devices/EmergencyButton.png';
    if (type.contains('magnetic') || type.contains('contact')) return 'assets/devices/WirelessMagnetic.png';
    if (type.contains('repeater')) return 'assets/devices/WirelessRepeater.png';
    if (type.contains('transmitter')) return 'assets/devices/WirelessRepeater.png';
    if (type.contains('relay') || type.contains('output') || type.contains('module')) return 'assets/devices/wallswitch.png';
    if (type.contains('leak') || type.contains('water') || type.contains('flood')) return 'assets/devices/WaterLeakDetector.png';
    if (type.contains('glass')) return 'assets/devices/GlassBreakDetector.png';

    // 2. Name-based fallbacks
    if (n.contains('door') || n.contains('window')) return 'assets/devices/WirelessMagnetic.png';
    if (n.contains('motion')) return 'assets/devices/WirelessPIR.png';
    if (n.contains('smoke') || n.contains('fire')) return 'assets/devices/WirelessSmoke.png';
    if (n.contains('keypad')) return 'assets/devices/WirelessKeypad.png';
    if (n.contains('siren')) return 'assets/devices/InternalSiren.png';

    // Default fallback (Generic PIR)
    return 'assets/devices/WirelessPIR.png';
  }

  static IconData getIconData(String? detectorType, String name) {
    final type = normalizeDetectorType(detectorType);
    final n = name.toLowerCase();

    if (_match(type, ['pir', 'motion'])) {
      return Icons.sensors_rounded;
    }

    if (_match(type, ['magnetic', 'door', 'contact', 'magnatic'])) {
      return Icons.sensor_door_rounded;
    }

    if (_match(type, ['smoke', 'fire'])) {
      return Icons.local_fire_department_rounded;
    }

    if (_match(type, ['glass'])) {
      return Icons.broken_image_rounded;
    }

    if (_match(type, ['vibration', 'shock'])) {
      return Icons.vibration_rounded;
    }

    if (_match(type, ['water', 'flood'])) {
      return Icons.water_drop_rounded;
    }

    if (_match(type, ['gas'])) {
      return Icons.gas_meter_rounded;
    }

    if (_match(type, ['panic', 'emergency'])) {
      return Icons.notification_important_rounded;
    }

    // ---- fallback by name ----

    if (_match(n, ['door', 'entrance'])) {
      return Icons.sensor_door_rounded;
    }

    if (_match(n, ['window'])) {
      return Icons.window_rounded;
    }

    if (_match(n, ['motion'])) {
      return Icons.sensors_rounded;
    }

    if (_match(n, ['camera', 'cam'])) {
      return Icons.videocam_rounded;
    }

    if (_match(n, ['smoke', 'fire'])) {
      return Icons.local_fire_department_rounded;
    }

    if (_match(n, ['glass'])) {
      return Icons.broken_image_rounded;
    }

    return Icons.sensors_rounded;
  }

  static Color getStatusColor(String state, {bool tamper = false, bool isOnline = true}) {
    if (!isOnline) return AppTheme.outline;
    if (tamper || state == 'alarm') return AppTheme.error;
    if (state == 'open') return AppTheme.onTertiaryContainer;
    return AppTheme.secondary; // This is now Green
  }

  static bool _match(String value, List<String> keys) {
    return keys.any((k) => value.contains(k));
  }

  static String normalizeDetectorType(String? type) {
    if (type == null) return '';
    return type
        .toLowerCase()
        .replaceAll('wireless', '')
        .replaceAll('_', '')
        .trim();
  }

  static String formatDeviceTypeLabel(String? type, {String fallback = 'Device'}) {
    final raw = (type ?? '').trim();
    if (raw.isEmpty) return fallback;

    final normalized = raw.toLowerCase();
    switch (normalized) {
      case 'keyfob':
        return 'Keyfob';
      case 'keypad':
        return 'Keypad';
      case 'card_reader':
      case 'reader':
        return 'Reader';
      case 'output_module':
        return 'Output Module';
      case 'relay':
        return 'Relay';
      default:
        return raw
            .replaceAll(RegExp(r'[_-]+'), ' ')
            .replaceAllMapped(
              RegExp(r'(?<=[a-z])(?=[A-Z])'),
              (_) => ' ',
            )
            .split(' ')
            .where((part) => part.isNotEmpty)
            .map((part) => part[0].toUpperCase() + part.substring(1).toLowerCase())
            .join(' ');
    }
  }
}
