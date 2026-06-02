import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';

import '../../../core/theme/app_theme.dart';
import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

class GuardPatrolScreen extends ConsumerWidget {
  const GuardPatrolScreen({super.key, this.assignmentId});

  final String? assignmentId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final roundsAsync = ref.watch(guardPatrolRoundsProvider);
    
    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: const Text('Patrol Operations'),
      ),
      body: roundsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorState(onRetry: () => ref.invalidate(guardPatrolRoundsProvider)),
        data: (rounds) {
          final filtered = assignmentId == null
              ? rounds
              : rounds.where((r) => r.assignmentId == assignmentId).toList();
          
          if (filtered.isEmpty) {
            return const _EmptyPatrolState();
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(guardPatrolRoundsProvider),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: filtered.length,
              separatorBuilder: (_, __) => const SizedBox(height: 16),
              itemBuilder: (context, index) => _PatrolRoundCard(round: filtered[index]),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppTheme.primary,
        foregroundColor: AppTheme.onPrimary,
        onPressed: () => context.push('/guard/scan', extra: assignmentId),
        icon: const Icon(Icons.qr_code_scanner_rounded),
        label: const Text('Quick Scan'),
      ),
    );
  }
}

class _PatrolRoundCard extends ConsumerStatefulWidget {
  const _PatrolRoundCard({required this.round});
  final GuardPatrolRound round;

  @override
  ConsumerState<_PatrolRoundCard> createState() => _PatrolRoundCardState();
}

class _PatrolRoundCardState extends ConsumerState<_PatrolRoundCard> {
  bool _busy = false;

  Future<void> _scan(GuardPatrolCheckpoint checkpoint) async {
    setState(() => _busy = true);
    try {
      final pos = await readGuardPosition();
      final result = await ref.read(guardApiProvider).scanCheckpoint(
            patrolRoundId: widget.round.id,
            checkpointId: checkpoint.id,
            clientScanId: const Uuid().v4(),
            latitude: pos?.latitude,
            longitude: pos?.longitude,
            withinGeofence: pos != null,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result.queued ? 'Scan queued offline' : 'Checkpoint scanned'),
        ),
      );
      if (result.postOrders.isNotEmpty || result.checkpointInstructions.isNotEmpty) {
        await _showScanDetails(context, checkpoint, result);
      }
      ref.invalidate(guardPatrolRoundsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Scan failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _showScanDetails(
    BuildContext context,
    GuardPatrolCheckpoint checkpoint,
    GuardScanResult result,
  ) {
    return showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(checkpoint.name),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (result.checkpointInstructions.isNotEmpty)
                Text(result.checkpointInstructions, style: const TextStyle(fontWeight: FontWeight.w600)),
              ...result.postOrders.map(
                (order) => Padding(
                  padding: const EdgeInsets.only(top: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(order.title, style: Theme.of(ctx).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
                      const SizedBox(height: 4),
                      Text(order.body, style: Theme.of(ctx).textTheme.bodyMedium),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Understood')),
        ],
      ),
    );
  }

  Future<void> _complete() async {
    setState(() => _busy = true);
    try {
      await ref.read(guardApiProvider).completePatrol(widget.round.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Patrol completed')),
        );
        ref.invalidate(guardPatrolRoundsProvider);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Complete failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final round = widget.round;
    final theme = Theme.of(context);
    final completedCount = round.scannedCheckpointIds.length;
    final totalCount = round.route.checkpoints.length;
    final progress = totalCount > 0 ? completedCount / totalCount : 0.0;

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.outlineVariant.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            round.routeName.toUpperCase(),
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: AppTheme.onSurfaceVariant,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.1,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            round.siteName.isNotEmpty ? round.siteName : 'Unspecified Site',
                            style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                          ),
                        ],
                      ),
                    ),
                    _StatusChip(status: round.status),
                  ],
                ),
                const SizedBox(height: 20),
                LinearProgressIndicator(
                  value: progress,
                  backgroundColor: AppTheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(100),
                  minHeight: 8,
                ),
                const SizedBox(height: 8),
                Text(
                  '$completedCount of $totalCount checkpoints completed',
                  style: theme.textTheme.labelSmall?.copyWith(color: AppTheme.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: round.route.checkpoints.length,
            separatorBuilder: (_, __) => const Divider(height: 1, indent: 56),
            itemBuilder: (context, idx) {
              final checkpoint = round.route.checkpoints[idx];
              final done = round.isComplete(checkpoint.id);
              return Material(
                color: AppTheme.surfaceContainerLowest, // Moved color here from outer container if needed, but this is a list item
                child: ListTile(
                  leading: Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: done ? AppTheme.secondary.withValues(alpha: 0.1) : AppTheme.surfaceContainerLow,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      done ? Icons.check_rounded : Icons.location_on_rounded,
                      size: 16,
                      color: done ? AppTheme.secondary : AppTheme.outline,
                    ),
                  ),
                  title: Text(
                    checkpoint.name,
                    style: TextStyle(
                      fontWeight: done ? FontWeight.w600 : FontWeight.w500,
                      color: done ? AppTheme.onSurface : AppTheme.onSurfaceVariant,
                    ),
                  ),
                  trailing: done 
                    ? null 
                    : IconButton(
                        icon: const Icon(Icons.qr_code_scanner_rounded, size: 20),
                        onPressed: _busy ? null : () => _scan(checkpoint),
                      ),
                ),
              );
            },
          ),
          if (progress == 1.0 && round.status != 'completed') ...[
            Padding(
              padding: const EdgeInsets.all(16),
              child: FilledButton(
                onPressed: _busy ? null : _complete,
                child: const Text('Finish Patrol Round'),
              ),
            ),
          ],
          const SizedBox(height: 8),
        ],
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
      'completed' => AppTheme.secondary,
      'in_progress' => Colors.blue,
      'scheduled' => Colors.orange,
      _ => AppTheme.onSurfaceVariant,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(100),
      ),
      child: Text(
        status.toUpperCase(),
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

class _EmptyPatrolState extends StatelessWidget {
  const _EmptyPatrolState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.route_rounded, size: 64, color: AppTheme.outlineVariant.withValues(alpha: 0.2)),
          const SizedBox(height: 16),
          Text(
            'No active patrol rounds.',
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
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('Could not load patrols'),
          const SizedBox(height: 16),
          FilledButton.tonal(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
