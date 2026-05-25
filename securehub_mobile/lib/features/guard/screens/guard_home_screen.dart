import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth_notifier.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';
import '../widgets/guard_welfare_banner.dart';

class GuardHomeScreen extends ConsumerWidget {
  const GuardHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(guardWelfareChecksProvider);
    final shiftsAsync = ref.watch(guardShiftsProvider);
    final auth = ref.watch(authNotifierProvider);
    final displayName = auth is AuthAuthenticated ? _guardDisplayName(auth) : '';

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Guard Operations'),
            if (displayName.isNotEmpty)
              Text(
                displayName,
                style: Theme.of(context).textTheme.labelSmall,
              ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Field report',
            icon: const Icon(Icons.description_outlined),
            onPressed: () => context.push('/guard/report'),
          ),
          IconButton(
            tooltip: 'Patrol rounds',
            icon: const Icon(Icons.route_outlined),
            onPressed: () => context.push('/guard/patrols'),
          ),
          IconButton(
            tooltip: 'SOS',
            icon: const Icon(Icons.local_police_outlined, color: Colors.red),
            onPressed: () => context.push('/guard/panic'),
          ),
          IconButton(
            tooltip: 'Dispatch',
            icon: const Icon(Icons.assignment_outlined),
            onPressed: () => context.push('/guard/dispatch'),
          ),
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authNotifierProvider.notifier).logout(),
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const GuardWelfareBanner(),
          Expanded(
            child: shiftsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Unable to load shifts: $err', textAlign: TextAlign.center),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => ref.invalidate(guardShiftsProvider),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
        data: (shifts) {
          if (shifts.isEmpty) {
            return const Center(child: Text('No shift assignments.'));
          }
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(guardShiftsProvider);
              ref.invalidate(guardWelfareChecksProvider);
            },
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: shifts.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final shift = shifts[index];
                return _ShiftCard(shift: shift, schedule: _formatSchedule(shift.startsAt, shift.endsAt));
              },
            ),
          );
        },
            ),
          ),
        ],
      ),
    );
  }
}

String _guardDisplayName(AuthAuthenticated auth) {
  final user = auth.profile.user;
  final name = '${user.firstName} ${user.lastName}'.trim();
  return name.isNotEmpty ? name : user.username;
}

String _formatSchedule(DateTime? start, DateTime? end) {
  if (start == null) return '';
  String two(int n) => n.toString().padLeft(2, '0');
  final s = '${two(start.day)}/${two(start.month)} ${two(start.hour)}:${two(start.minute)}';
  if (end == null) return s;
  return '$s – ${two(end.hour)}:${two(end.minute)}';
}

class _ShiftCard extends StatelessWidget {
  const _ShiftCard({required this.shift, required this.schedule});

  final GuardShiftAssignment shift;
  final String schedule;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        title: Text(shift.displayTitle),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            _StatusChip(status: shift.status),
            if (schedule.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(schedule, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push('/guard/shift/${shift.id}', extra: shift),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'clocked_in' => Colors.green,
      'accepted' => Colors.blue,
      'assigned' => Colors.orange,
      _ => Colors.grey,
    };
    return Chip(
      visualDensity: VisualDensity.compact,
      label: Text(status.replaceAll('_', ' ')),
      side: BorderSide(color: color.withValues(alpha: 0.5)),
      labelStyle: TextStyle(color: color, fontSize: 12),
    );
  }
}
