import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/theme/app_theme.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';
import '../widgets/active_shift_header.dart';
import '../widgets/guard_quick_actions.dart';
import '../widgets/guard_stat_card.dart';
import '../widgets/guard_welfare_banner.dart';

class GuardHomeScreen extends ConsumerWidget {
  const GuardHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shiftsAsync = ref.watch(guardShiftsProvider);
    final auth = ref.watch(authNotifierProvider);
    final displayName = auth is AuthAuthenticated ? _guardDisplayName(auth) : '';

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Guard Operations',
              style: Theme.of(context).appBarTheme.titleTextStyle,
            ),
            if (displayName.isNotEmpty)
              Text(
                displayName,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: AppTheme.onSurfaceVariant,
                      fontWeight: FontWeight.w600,
                    ),
              ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout_rounded),
            onPressed: () => ref.read(authNotifierProvider.notifier).logout(),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(guardShiftsProvider);
          ref.invalidate(guardWelfareChecksProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const GuardWelfareBanner(),
              shiftsAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (err, _) => _ErrorState(onRetry: () => ref.invalidate(guardShiftsProvider)),
                data: (shifts) {
                  // Find currently clocked in shift
                  final clockedInShift = shifts.cast<GuardShiftAssignment?>().firstWhere(
                    (s) => s?.isClockedIn ?? false,
                    orElse: () => null,
                  );

                  // If no one is clocked in, the "Active" area shows the first upcoming one
                  final displayActiveShift = clockedInShift ?? (shifts.isNotEmpty ? shifts.first : null);
                  final hasAssignments = shifts.isNotEmpty;
                  
                  return Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (displayActiveShift != null) ...[
                          ActiveShiftHeader(shift: displayActiveShift),
                          const SizedBox(height: 24),
                          const _StatsGrid(),
                          const SizedBox(height: 32),
                        ] else ...[
                          const _EmptyState(),
                        ],
                        
                        Text(
                          'COMMAND CENTER',
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: AppTheme.onSurfaceVariant,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1.2,
                              ),
                        ),
                        const SizedBox(height: 16),
                        _QuickActionsSection(),
                        
                        if (shifts.length > 1) ...[
                          const SizedBox(height: 32),
                          Row(
                            children: [
                              Text(
                                'ALL ASSIGNMENTS',
                                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: AppTheme.onSurfaceVariant,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 1.2,
                                    ),
                              ),
                              const Spacer(),
                              Text(
                                '${shifts.length}',
                                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: AppTheme.onSurfaceVariant,
                                      fontWeight: FontWeight.w600,
                                    ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: shifts.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 8),
                            itemBuilder: (context, index) {
                              final shift = shifts[index];
                              // We still show the active one in the list for navigation/detail access
                              return _ShiftListItem(shift: shift);
                            },
                          ),
                        ],
                        const SizedBox(height: 40),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  const _StatsGrid();

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      height: 100, // Constrain height to prevent layout errors
      child: Row(
        children: [
          Expanded(
            child: GuardStatCard(
              label: 'Shift Time',
              value: '04:12',
              icon: Icons.timer_outlined,
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: GuardStatCard(
              label: 'Scans',
              value: '12/15',
              icon: Icons.qr_code_scanner_rounded,
              color: AppTheme.secondary,
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: GuardStatCard(
              label: 'Tasks',
              value: '2',
              icon: Icons.assignment_turned_in_outlined,
            ),
          ),
        ],
      ),
    );
  }
}

class _QuickActionsSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GuardQuickActionsRow(
      actions: [
        GuardQuickAction(
          icon: Icons.local_police_rounded,
          label: 'PANIC/SOS',
          isDestructive: true,
          onTap: () => context.push('/guard/panic'),
        ),
        GuardQuickAction(
          icon: Icons.route_rounded,
          label: 'PATROL',
          onTap: () => context.push('/guard/patrols'),
        ),
        GuardQuickAction(
          icon: Icons.edit_document,
          label: 'REPORT',
          onTap: () => context.push('/guard/report'),
        ),
        GuardQuickAction(
          icon: Icons.assignment_ind_rounded,
          label: 'DISPATCH',
          onTap: () => context.push('/guard/dispatch'),
        ),
        GuardQuickAction(
          icon: Icons.medical_services_rounded,
          label: 'WELFARE',
          onTap: () => context.push('/guard/welfare'),
        ),
      ],
    );
  }
}

class _UpcomingShiftPreview extends StatelessWidget {
  const _UpcomingShiftPreview({required this.shift});
  final GuardShiftAssignment shift;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.calendar_today_rounded, size: 16, color: AppTheme.onSurfaceVariant),
              const SizedBox(width: 8),
              Text(
                'UPCOMING ASSIGNMENT',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: AppTheme.onSurfaceVariant,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            shift.siteName,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          Text(
            shift.postName,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.onSurfaceVariant),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => context.push('/guard/shift/${shift.id}', extra: shift),
              child: const Text('View Details'),
            ),
          ),
        ],
      ),
    );
  }
}

class _ShiftListItem extends StatelessWidget {
  const _ShiftListItem({required this.shift});
  final GuardShiftAssignment shift;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.surfaceContainerLowest, // Background color must be on Material
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => context.push('/guard/shift/${shift.id}', extra: shift),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border.all(color: AppTheme.outlineVariant.withValues(alpha: 0.1)),
            borderRadius: BorderRadius.circular(16),
            // REMOVED color: AppTheme.surfaceContainerLowest - Handled by Material
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      shift.siteName,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    Text(
                      shift.postName,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppTheme.onSurfaceVariant),
                    ),
                  ],
                ),
              ),
              _StatusBadge(status: shift.status),
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right_rounded, color: AppTheme.outlineVariant),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'clocked_in' => AppTheme.secondary,
      'accepted' => Colors.blue,
      'assigned' => Colors.orange,
      _ => AppTheme.onSurfaceVariant,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        status.replaceAll('_', ' ').toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 9,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48),
      child: Column(
        children: [
          Icon(Icons.assignment_turned_in_outlined, size: 64, color: AppTheme.outlineVariant.withValues(alpha: 0.2)),
          const SizedBox(height: 16),
          Text(
            'No assignments scheduled.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          children: [
            const Text('Unable to load dashboard', textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton.tonal(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

String _guardDisplayName(AuthAuthenticated auth) {
  final user = auth.profile.user;
  final name = '${user.firstName} ${user.lastName}'.trim();
  return name.isNotEmpty ? name : user.username;
}
