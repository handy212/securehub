import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

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
    return Scaffold(
      appBar: AppBar(title: Text(assignment.postName)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(assignment.siteName, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('Status: ${assignment.statusLabel}'),
            const SizedBox(height: 24),
            if (assignment.canAccept)
              FilledButton(
                onPressed: _busy
                    ? null
                    : () => _run(
                          () => ref.read(guardApiProvider).acceptShift(assignment.id),
                          'Shift accepted',
                        ),
                child: const Text('Accept shift'),
              ),
            if (assignment.canAccept) const SizedBox(height: 8),
            FilledButton(
              onPressed: _busy || !assignment.canClockIn ? null : () => _clock('clock_in'),
              child: const Text('Clock in'),
            ),
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: _busy || !assignment.canClockOut ? null : () => _clock('clock_out'),
              child: const Text('Clock out'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => context.push('/guard/patrols', extra: assignment.id),
              child: const Text('Patrol rounds'),
            ),
            if (assignment.isClockedIn) ...[
              const SizedBox(height: 8),
              OutlinedButton(
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
                child: const Text('Send location ping'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
