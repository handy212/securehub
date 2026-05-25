import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';

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
      appBar: AppBar(
        title: const Text('Patrol rounds'),
        actions: [
          IconButton(
            tooltip: 'Scan QR',
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: () => context.push(
              '/guard/scan',
              extra: assignmentId,
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/guard/scan', extra: assignmentId),
        icon: const Icon(Icons.qr_code_scanner),
        label: const Text('Scan QR'),
      ),
      body: roundsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (rounds) {
          final filtered = assignmentId == null
              ? rounds
              : rounds.where((r) => r.assignmentId == assignmentId).toList();
          if (filtered.isEmpty) {
            return const Center(child: Text('No patrol rounds scheduled.'));
          }
          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: filtered.length,
            itemBuilder: (context, index) => _PatrolRoundCard(round: filtered[index]),
          );
        },
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
                Text(result.checkpointInstructions),
              ...result.postOrders.map(
                (order) => Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(order.title, style: Theme.of(ctx).textTheme.titleSmall),
                      Text(order.body),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
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
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(round.routeName, style: Theme.of(context).textTheme.titleMedium),
            if (round.siteName.isNotEmpty) Text(round.siteName),
            Text('Status: ${round.status}'),
            const SizedBox(height: 8),
            ...round.route.checkpoints.map((checkpoint) {
              final done = round.isComplete(checkpoint.id);
              return ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  done ? Icons.check_circle : Icons.radio_button_unchecked,
                  color: done ? Colors.green : null,
                  size: 20,
                ),
                title: Text(checkpoint.name),
                subtitle: checkpoint.code.isNotEmpty ? Text('Code: ${checkpoint.code}') : null,
                trailing: TextButton(
                  onPressed: _busy || done ? null : () => _scan(checkpoint),
                  child: const Text('Scan'),
                ),
              );
            }),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _busy ? null : _complete,
              child: const Text('Complete patrol'),
            ),
          ],
        ),
      ),
    );
  }
}
