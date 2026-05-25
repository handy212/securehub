import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

class GuardWelfareBanner extends ConsumerWidget {
  const GuardWelfareBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final urgent = ref.watch(guardUrgentWelfareProvider);
    if (urgent.isEmpty) return const SizedBox.shrink();

    final check = urgent.first;
    final dueLabel = DateFormat.Hm().format(check.dueAt.toLocal());
    final color = check.isOverdue ? Colors.red.shade700 : Colors.orange.shade800;

    return Card(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      color: check.isOverdue ? Colors.red.shade50 : Colors.orange.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(Icons.health_and_safety_outlined, color: color),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    check.isOverdue ? 'Welfare check overdue' : 'Welfare check due soon',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(color: color),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${check.siteName} · ${check.postName} — due $dueLabel',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                FilledButton(
                  onPressed: () => _confirm(context, ref, check),
                  child: const Text('I am OK'),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: () => context.push('/guard/welfare'),
                  child: const Text('View all'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirm(BuildContext context, WidgetRef ref, GuardWelfareCheck check) async {
    try {
      await ref.read(guardApiProvider).confirmWelfareCheck(check.id);
      ref.invalidate(guardWelfareChecksProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Welfare check confirmed')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not confirm: $e')),
        );
      }
    }
  }
}
