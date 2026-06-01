import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../models/guard_models.dart';

class ActiveShiftHeader extends StatelessWidget {
  const ActiveShiftHeader({
    super.key,
    required this.shift,
  });

  final GuardShiftAssignment shift;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final startTime = shift.startsAt != null ? DateFormat.Hm().format(shift.startsAt!) : '--:--';
    final endTime = shift.endsAt != null ? DateFormat.Hm().format(shift.endsAt!) : '--:--';

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.primaryContainer,
        borderRadius: BorderRadius.circular(24),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.secondary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: AppTheme.secondary.withValues(alpha: 0.2)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: AppTheme.secondary,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'ACTIVE SHIFT',
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: AppTheme.secondary,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              Text(
                '$startTime — $endTime',
                style: theme.textTheme.labelMedium?.copyWith(
                  color: AppTheme.onPrimaryContainer,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            shift.siteName,
            style: theme.textTheme.headlineSmall?.copyWith(
              color: AppTheme.onPrimary,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            shift.postName,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: AppTheme.onPrimaryContainer,
            ),
          ),
        ],
      ),
    );
  }
}
