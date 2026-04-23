import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';

class SubsystemCard extends StatelessWidget {
  const SubsystemCard({
    super.key,
    required this.subsystem,
    required this.onTap,
  });

  final Subsystem subsystem;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final hasAlarm = subsystem.status == 'alarm' ||
        subsystem.zones.any((z) => z.state == 'alarm' || z.tamper);
    final isArmedAway = subsystem.status == 'armed';
    final isArmedStay = subsystem.status == 'stay';
    final isArmed = isArmedAway || isArmedStay;

    final Color statusColor = hasAlarm
        ? AppTheme.error
        : (isArmed ? AppTheme.primary : AppTheme.secondary);

    final IconData statusIcon = hasAlarm
        ? Icons.gpp_maybe_rounded
        : (isArmedAway
            ? Icons.gpp_good_rounded
            : (isArmedStay ? Icons.home_rounded : Icons.shield_outlined));

    final openZonesCount =
        subsystem.zones.where((z) => z.state == 'open' && !z.tamper).length;
    final alarmZonesCount =
        subsystem.zones.where((z) => z.state == 'alarm' || z.tamper).length;
    final issueCount = alarmZonesCount > 0 ? alarmZonesCount : openZonesCount;
    final issueLabel = alarmZonesCount > 0 ? 'Alarm' : 'Open';
    final statusLabel = isArmedAway
        ? 'Armed Away'
        : isArmedStay
            ? 'Armed Stay'
            : hasAlarm
                ? 'Alarm'
                : 'Disarmed';

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(22),
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: AppTheme.outlineVariant.withValues(alpha: 0.16),
              ),
              image: const DecorationImage(
                image: AssetImage('assets/images/area.png'),
                fit: BoxFit.cover,
              ),
            ),
            child: Stack(
              children: [
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(22),
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.black.withValues(alpha: 0.08),
                          Colors.black.withValues(alpha: 0.18),
                          Colors.black.withValues(alpha: 0.45),
                        ],
                        stops: const [0.0, 0.45, 1.0],
                      ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Stack(
                    children: [
                      Align(
                        alignment: Alignment.topLeft,
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _GlassBadge(
                              child: Icon(
                                statusIcon,
                                color: statusColor,
                                size: 18,
                              ),
                            ),
                            const Spacer(),
                            if (issueCount > 0)
                              _StatusPill(
                                count: issueCount,
                                label: issueLabel,
                                isError: alarmZonesCount > 0,
                              ),
                          ],
                        ),
                      ),
                      Align(
                        alignment: Alignment.bottomLeft,
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.82),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.34),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                subsystem.name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 12,
                                  color: AppTheme.primary,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Wrap(
                                spacing: 4,
                                runSpacing: 4,
                                children: [
                                  _TagPill(
                                    label: statusLabel,
                                    foreground: statusColor,
                                    background: statusColor.withValues(
                                      alpha: 0.12,
                                    ),
                                  ),
                                  if (openZonesCount > 0)
                                    _TagPill(
                                      label: '$openZonesCount open',
                                      foreground:
                                          AppTheme.onTertiaryContainer,
                                      background:
                                          AppTheme.tertiaryFixed.withValues(
                                        alpha: 0.92,
                                      ),
                                    ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _GlassBadge extends StatelessWidget {
  const _GlassBadge({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.42)),
      ),
      child: child,
    );
  }
}

class _TagPill extends StatelessWidget {
  const _TagPill({
    required this.label,
    required this.foreground,
    required this.background,
  });

  final String label;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
          fontSize: 8,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.35,
          color: foreground,
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill(
      {required this.count, required this.label, required this.isError});
  final int count;
  final String label;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isError
            ? AppTheme.errorContainer.withValues(alpha: 0.92)
            : Colors.white.withValues(alpha: 0.76),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isError
              ? AppTheme.error.withValues(alpha: 0.12)
              : AppTheme.outlineVariant.withValues(alpha: 0.18),
        ),
      ),
      child: Text(
        '$count ${label.toUpperCase()}',
        style: GoogleFonts.inter(
          color: isError ? AppTheme.error : AppTheme.onTertiaryContainer,
          fontSize: 8,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
