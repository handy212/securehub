import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';

class SubsystemCard extends StatelessWidget {
  const SubsystemCard({
    super.key,
    required this.subsystem,
    required this.onTap,
    this.onArmAway,
    this.onArmStay,
    this.isHero = false,
  });

  final Subsystem subsystem;
  final VoidCallback onTap;
  final VoidCallback? onArmAway;
  final VoidCallback? onArmStay;
  final bool isHero;

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

    final cardBg = AppTheme.surfaceContainerLowest;
    final borderColor = hasAlarm
        ? AppTheme.error.withValues(alpha: 0.3)
        : (isArmed
            ? AppTheme.primary.withValues(alpha: 0.2)
            : AppTheme.outlineVariant.withValues(alpha: 0.16));

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
            padding: EdgeInsets.all(isHero ? 20 : 12),
            decoration: BoxDecoration(
              color: cardBg,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: borderColor,
                width: hasAlarm || isArmed ? 1.5 : 1,
              ),
              image: DecorationImage(
                image: const AssetImage('assets/images/area.png'),
                fit: BoxFit.cover,
                opacity: 0.06, // Faded background image
                colorFilter: ColorFilter.mode(
                  cardBg.withValues(alpha: 0.9),
                  BlendMode.screen,
                ),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: EdgeInsets.all(isHero ? 12 : 10),
                            decoration: BoxDecoration(
                              color: statusColor.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Icon(
                              statusIcon,
                              color: statusColor,
                              size: isHero ? 24 : 18,
                            ),
                          ),
                          const SizedBox(width: 8),
                          if (issueCount > 0)
                            _StatusPill(
                              count: issueCount,
                              label: issueLabel,
                              isError: alarmZonesCount > 0,
                            ),
                        ],
                      ),
                      const Spacer(),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            subsystem.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.w800,
                              fontSize: isHero ? 18 : 12,
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
                                  foreground: AppTheme.onTertiaryContainer,
                                  background: AppTheme.tertiaryFixed.withValues(
                                    alpha: 0.92,
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (isHero) ...[
                  const SizedBox(width: 16),
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _QuickActionCircle(
                        icon: Icons.exit_to_app_rounded,
                        color: isArmedAway ? AppTheme.primary : AppTheme.secondary,
                        isActive: isArmedAway,
                        onTap: onArmAway,
                        tooltip: 'Arm Away',
                      ),
                      const SizedBox(height: 12),
                      _QuickActionCircle(
                        icon: Icons.home_rounded,
                        color: isArmedStay ? AppTheme.primary : AppTheme.secondary,
                        isActive: isArmedStay,
                        onTap: onArmStay,
                        tooltip: 'Arm Stay',
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _QuickActionCircle extends StatelessWidget {
  const _QuickActionCircle({
    required this.icon,
    required this.color,
    required this.isActive,
    required this.onTap,
    required this.tooltip,
  });

  final IconData icon;
  final Color color;
  final bool isActive;
  final VoidCallback? onTap;
  final String tooltip;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: GestureDetector(
        onTap: () {
          HapticFeedback.lightImpact();
          onTap?.call();
        },
        child: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: isActive ? color : Colors.white,
            shape: BoxShape.circle,
            border: Border.all(
              color: isActive ? Colors.transparent : AppTheme.outlineVariant.withValues(alpha: 0.2),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Icon(
            icon,
            color: isActive ? Colors.white : color,
            size: 20,
          ),
        ),
      ),
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
