import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
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
    final color = check.isOverdue ? AppTheme.error : Colors.orange.shade800;
    final bgColor = check.isOverdue ? AppTheme.errorContainer.withValues(alpha: 0.5) : Colors.orange.shade50;

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.health_and_safety_rounded, color: color, size: 20),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  check.isOverdue ? 'Safety check overdue' : 'Safety check required',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Text(
                dueLabel,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: color.withValues(alpha: 0.7),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: color,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: () => _confirm(context, ref, check),
                  child: const Text('I am Safe & OK'),
                ),
              ),
            ],
          ),
        ],
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
