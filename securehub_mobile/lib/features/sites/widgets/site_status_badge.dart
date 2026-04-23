import 'package:flutter/material.dart';
import '../../../core/models/site_poll.dart';
import '../../../core/theme/app_theme.dart';

class SiteStatusBadge extends StatelessWidget {
  const SiteStatusBadge({super.key, required this.poll});

  final SitePoll poll;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final hasAlarm = poll.activeAlarmCount > 0;
    final hasOffline = poll.offlineDeviceCount > 0;

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (hasAlarm)
          _StatusPill(
            label: 'ALARM',
            color: AppTheme.error,
            showDot: true,
          )
        else if (poll.armedSubsystems > 0)
          _StatusPill(
            label: '${poll.armedSubsystems} Armed',
            color: AppTheme.primary,
            showDot: true,
          ),
        if (poll.disarmedSubsystems > 0)
          _StatusPill(
            label: '${poll.disarmedSubsystems} Ready',
            color: AppTheme.secondary,
            showDot: true,
          ),
        if (hasOffline)
          _StatusPill(
            label: '${poll.offlineDeviceCount} Offline',
            color: AppTheme.onSurfaceVariant,
            isOutline: true,
          ),
      ],
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({
    required this.label,
    required this.color,
    this.isOutline = false,
    this.showDot = false,
  });

  final String label;
  final Color color;
  final bool isOutline;
  final bool showDot;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: isOutline ? Colors.transparent : color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isOutline ? color.withValues(alpha: 0.3) : color.withValues(alpha: 0.1),
          width: 0.8,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showDot) ...[
            Container(
              width: 5,
              height: 5,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: color.withValues(alpha: 0.5),
                    blurRadius: 4,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
          ],
          Text(
            label.toUpperCase(),
            style: TextStyle(
              fontSize: 8.5,
              color: isOutline ? color.withValues(alpha: 0.8) : color,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
            ),
          ),
        ],
      ),
    );
  }
}
