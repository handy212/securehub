import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

class ShiftDetailScreen extends ConsumerStatefulWidget {
  const ShiftDetailScreen({super.key, required this.assignment});

  final GuardShiftAssignment assignment;

  @override
  ConsumerState<ShiftDetailScreen> createState() => _ShiftDetailScreenState();
}

class _ShiftDetailScreenState extends ConsumerState<ShiftDetailScreen> {
  bool _busy = false;

  Future<void> _run(Future<void> Function() action, String successMessage) async {
    setState(() => _busy = true);
    try {
      await action();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(successMessage)));
        ref.invalidate(guardShiftsProvider);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Action failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _clock(String eventType) async {
    final pos = await readGuardPosition();
    await _run(
      () => ref.read(guardApiProvider).clockEvent(
            assignmentId: widget.assignment.id,
            eventType: eventType,
            latitude: pos?.latitude,
            longitude: pos?.longitude,
            accuracyM: pos?.accuracy,
            withinGeofence: pos != null,
          ),
      eventType == 'clock_in' ? 'Clocked in' : 'Clocked out',
    );
  }

  @override
  Widget build(BuildContext context) {
    final assignment = widget.assignment;
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: const Text('Assignment Details'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.surfaceContainerLowest,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: AppTheme.outlineVariant.withValues(alpha: 0.1)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _StatusBadge(status: assignment.status),
                  const SizedBox(height: 16),
                  Text(
                    assignment.siteName,
                    style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    assignment.postName,
                    style: theme.textTheme.titleMedium?.copyWith(color: AppTheme.onSurfaceVariant),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      const Icon(Icons.location_on_rounded, size: 16, color: AppTheme.onSurfaceVariant),
                      const SizedBox(width: 8),
                      Text(
                        'Site Location Active',
                        style: theme.textTheme.labelSmall?.copyWith(color: AppTheme.onSurfaceVariant, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
            Text(
              'OPERATIONS',
              style: theme.textTheme.labelSmall?.copyWith(
                color: AppTheme.onSurfaceVariant,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 16),
            if (assignment.canAccept) ...[
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: AppTheme.secondary),
                onPressed: _busy
                    ? null
                    : () => _run(
                          () => ref.read(guardApiProvider).acceptShift(assignment.id),
                          'Shift accepted',
                        ),
                child: const Text('Accept Assignment'),
              ),
              const SizedBox(height: 12),
            ],
            if (assignment.canClockIn) ...[
              FilledButton(
                onPressed: _busy ? null : () => _clock('clock_in'),
                child: const Text('Clock In'),
              ),
              const SizedBox(height: 12),
            ],
            if (assignment.canClockOut) ...[
              FilledButton.tonal(
                style: FilledButton.styleFrom(backgroundColor: AppTheme.error.withValues(alpha: 0.1), foregroundColor: AppTheme.error),
                onPressed: _busy ? null : () => _clock('clock_out'),
                child: const Text('Clock Out'),
              ),
              const SizedBox(height: 12),
            ],
            OutlinedButton(
              onPressed: () => context.push('/guard/patrols', extra: assignment.id),
              child: const Text('View Patrol Rounds'),
            ),
            const SizedBox(height: 12),
            if (assignment.isClockedIn) ...[
              OutlinedButton.icon(
                icon: const Icon(Icons.share_location_rounded, size: 18),
                onPressed: _busy
                    ? null
                    : () async {
                        final pos = await readGuardPosition();
                        if (pos == null) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Location permission required')),
                            );
                          }
                          return;
                        }
                        await _run(
                          () => ref.read(guardApiProvider).sendLocationPing(
                                assignmentId: assignment.id,
                                latitude: pos.latitude,
                                longitude: pos.longitude,
                                accuracyM: pos.accuracy,
                              ),
                          'Location ping sent',
                        );
                      },
                label: const Text('Send Location Ping'),
              ),
            ],
          ],
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
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(100),
      ),
      child: Text(
        status.replaceAll('_', ' ').toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
