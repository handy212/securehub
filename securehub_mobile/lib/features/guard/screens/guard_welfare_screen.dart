import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

class GuardWelfareScreen extends ConsumerWidget {
  const GuardWelfareScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checksAsync = ref.watch(guardWelfareChecksProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Welfare checks')),
      body: checksAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (checks) {
          if (checks.isEmpty) {
            return const Center(child: Text('No pending welfare checks.'));
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(guardWelfareChecksProvider),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: checks.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
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
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Welfare check confirmed')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final check = widget.check;
    final due = DateFormat('EEE d MMM, HH:mm').format(check.dueAt.toLocal());
    return Card(
      color: check.isOverdue ? Colors.red.shade50 : null,
      child: ListTile(
        title: Text('${check.siteName} — ${check.postName}'),
        subtitle: Text('Due $due · ${check.status.replaceAll('_', ' ')}'),
        trailing: check.isPending
            ? FilledButton(
                onPressed: _busy ? null : _confirm,
                child: _busy
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Confirm'),
              )
            : null,
      ),
    );
  }
}
