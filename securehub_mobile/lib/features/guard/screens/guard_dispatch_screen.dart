import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

class GuardDispatchScreen extends ConsumerWidget {
  const GuardDispatchScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasksAsync = ref.watch(guardDispatchProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Dispatch tasks')),
      body: tasksAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (tasks) {
          if (tasks.isEmpty) {
            return const Center(child: Text('No dispatch tasks assigned.'));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: tasks.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) => _DispatchCard(task: tasks[index]),
          );
        },
      ),
    );
  }
}

class _DispatchCard extends ConsumerWidget {
  const _DispatchCard({required this.task});

  final GuardDispatchTask task;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final action = task.nextAction;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(task.title, style: Theme.of(context).textTheme.titleMedium),
            if (task.siteName != null) Text(task.siteName!),
            Text(task.description),
            Text('Priority: ${task.priority} · Status: ${task.status}'),
            if (action != null) ...[
              const SizedBox(height: 8),
              FilledButton(
                onPressed: () => _transition(ref, context, task.id, action),
                child: Text(task.nextActionLabel),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _transition(
    WidgetRef ref,
    BuildContext context,
    String id,
    String action,
  ) async {
    try {
      await ref.read(guardApiProvider).transitionDispatch(id, action);
      ref.invalidate(guardDispatchProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Updated: ${action.replaceAll('-', ' ')}')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e')),
        );
      }
    }
  }
}
