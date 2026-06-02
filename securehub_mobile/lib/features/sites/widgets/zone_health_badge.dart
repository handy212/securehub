import 'package:flutter/material.dart';

import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';

/// Compact health indicator row shown beneath a zone's name.
/// Renders nothing if the zone has no health warnings.
class ZoneHealthBadge extends StatelessWidget {
  const ZoneHealthBadge({super.key, required this.zone});

  final Zone zone;

  @override
  Widget build(BuildContext context) {
    final issues = _issues(context);
    if (issues.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 4,
      runSpacing: 2,
      children: issues,
    );
  }

  List<Widget> _issues(BuildContext context) {
    final items = <Widget>[];

    if (zone.lowBattery) {
      items.add(const _HealthTag(
        icon: Icons.battery_alert,
        label: 'Low battery',
        color: AppTheme.errorContainer,
        onColor: AppTheme.onErrorContainer,
      ));
    }
    if (zone.tamper) {
      items.add(const _HealthTag(
        icon: Icons.report_gmailerrorred_rounded,
        label: 'Tamper',
        color: AppTheme.errorContainer,
        onColor: AppTheme.onErrorContainer,
      ));
    }
    final sig = zone.signalStrength.toLowerCase();
    final isPoorSignal = sig == 'weak' || sig == 'poor' || sig == 'none' || sig == 'disconnected' || sig == 'lost';
    
    if (zone.signalStrength.isNotEmpty && isPoorSignal) {
      items.add(_HealthTag(
        icon: Icons.signal_cellular_alt_rounded,
        label: 'Signal: ${zone.signalStrength}',
        color: sig == 'lost' || sig == 'disconnected' ? AppTheme.errorContainer : AppTheme.surfaceContainerHigh,
        onColor: sig == 'lost' || sig == 'disconnected' ? AppTheme.onErrorContainer : AppTheme.onSurfaceVariant,
      ));
    }

    return items;
  }
}

class _HealthTag extends StatelessWidget {
  const _HealthTag({
    required this.icon,
    required this.label,
    required this.color,
    required this.onColor,
  });

  final IconData icon;
  final String label;
  final Color color;
  final Color onColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: onColor),
          const SizedBox(width: 4),
          Text(label,
              style: TextStyle(
                  fontSize: 9, color: onColor, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

