import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

class GuardWelfareScreen extends ConsumerWidget {
  const GuardWelfareScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checksAsync = ref.watch(guardWelfareChecksProvider);
    
    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: const Text('Safety Checks'),
      ),
      body: checksAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorState(onRetry: () => ref.invalidate(guardWelfareChecksProvider)),
        data: (checks) {
          if (checks.isEmpty) {
            return const _EmptyWelfareState();
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(guardWelfareChecksProvider),
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: checks.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) => _WelfareCard(check: checks[index]),
            ),
          );
        },
      ),
    );
  }
}

class _WelfareCard extends ConsumerStatefulWidget {
  const _WelfareCard({required this.check});
  final GuardWelfareCheck check;

  @override
  ConsumerState<_WelfareCard> createState() => _WelfareCardState();
}

class _WelfareCardState extends ConsumerState<_WelfareCard> {
  bool _busy = false;

  Future<void> _confirm() async {
    setState(() => _busy = true);
    try {
      await ref.read(guardApiProvider).confirmWelfareCheck(widget.check.id);
      ref.invalidate(guardWelfareChecksProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Status Confirmed: Safety Verified')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final check = widget.check;
    final theme = Theme.of(context);
    final due = DateFormat('HH:mm').format(check.dueAt.toLocal());
    final date = DateFormat('EEE d MMM').format(check.dueAt.toLocal());
    
    final isUrgent = check.isPending && (check.isOverdue || check.isDueSoon);
    final color = check.isOverdue ? AppTheme.error : (check.isPending ? Colors.orange : AppTheme.secondary);

    return Material(
      color: AppTheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: check.isPending ? () {} : null, // Empty callback to enable ink effect if pending
        child: Container(
          decoration: BoxDecoration(
            border: Border.all(
              color: isUrgent ? color.withValues(alpha: 0.3) : AppTheme.outlineVariant.withValues(alpha: 0.1),
              width: isUrgent ? 1.5 : 1,
            ),
            borderRadius: BorderRadius.circular(20),
            // REMOVED color: AppTheme.surfaceContainerLowest, - Moved to Material above
          ),
          child: ListTile(
            contentPadding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
            leading: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                check.isPending ? Icons.health_and_safety_rounded : Icons.check_circle_rounded,
                color: color,
                size: 24,
              ),
            ),
            title: Text(
              check.siteName,
              style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${check.postName} · $date'),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.access_time_rounded, size: 12, color: color),
                    const SizedBox(width: 4),
                    Text(
                      'Due $due',
                      style: theme.textTheme.labelSmall?.copyWith(color: color, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ],
            ),
            trailing: check.isPending
                ? FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: color,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
                      visualDensity: VisualDensity.compact,
                    ),
                    onPressed: _busy ? null : _confirm,
                    child: _busy
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('CONFIRM'),
                  )
                : Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.secondary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text('OK', style: TextStyle(color: AppTheme.secondary, fontSize: 10, fontWeight: FontWeight.w900)),
                  ),
          ),
        ),
      ),
    );
  }
}

class _EmptyWelfareState extends StatelessWidget {
  const _EmptyWelfareState();
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.health_and_safety_outlined, size: 64, color: AppTheme.outlineVariant.withValues(alpha: 0.2)),
          const SizedBox(height: 16),
          const Text('All safety checks completed.', style: TextStyle(color: AppTheme.onSurfaceVariant)),
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
          const Text('Could not load safety checks'),
          const SizedBox(height: 16),
          FilledButton.tonal(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
