import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/models/arm_disarm_command.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/command_list_provider.dart';

class CommandHistoryScreen extends ConsumerWidget {
  const CommandHistoryScreen({super.key, required this.siteId});
  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cmdsAsync = ref.watch(commandListProvider(siteId));

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: CustomScrollView(
        slivers: [
          // ── App Bar ──────────────────────────────────────────────────────
          SliverAppBar(
            pinned: true,
            backgroundColor: Colors.transparent,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            scrolledUnderElevation: 0,
            automaticallyImplyLeading: false,
            expandedHeight: 120,
            flexibleSpace: FlexibleSpaceBar(
              titlePadding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
              title: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Command History',
                      style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.primary,
                          letterSpacing: -0.5)),
                  Text('Audit logs for security commands',
                      style: TextStyle(
                          fontSize: 12, color: AppTheme.onSurfaceVariant)),
                ],
              ),
            ),
          ),

          // ── Commands ───────────────────────────────────────────────────────
          cmdsAsync.when(
            loading: () => const SliverFillRemaining(
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (err, _) => SliverFillRemaining(
              child: Center(
                  child: Text(err.toString(),
                      style: TextStyle(color: AppTheme.error))),
            ),
            data: (cmds) {
              if (cmds.isEmpty) {
                return SliverFillRemaining(
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(28),
                          decoration: BoxDecoration(
                            color: AppTheme.secondaryContainer.withValues(alpha: 0.3),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.shield_outlined,
                              size: 40, color: AppTheme.secondary),
                        ),
                        const SizedBox(height: 24),
                        Text('No commands found',
                            style: TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 18,
                                color: AppTheme.primary)),
                      ],
                    ),
                  ),
                );
              }
              return SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, i) => _CommandTile(cmd: cmds[i]),
                    childCount: cmds.length,
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _CommandTile extends StatelessWidget {
  const _CommandTile({required this.cmd});
  final ArmDisarmCommand cmd;

  @override
  Widget build(BuildContext context) {
    final dt = _parseDate(cmd.createdAt);
    final isOk = cmd.status == 'success';
    final isPending = cmd.status == 'pending';
    final statusColor = isOk
        ? AppTheme.secondary
        : (isPending ? AppTheme.onTertiaryContainer : AppTheme.error);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          // 4px tonal bar
          Container(
            width: 4,
            height: 72,
            decoration: BoxDecoration(
              color: statusColor,
              borderRadius:
                  const BorderRadius.horizontal(left: Radius.circular(16)),
            ),
          ),
          const SizedBox(width: 16),
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.08),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isOk
                  ? Icons.check_circle_outline_rounded
                  : (isPending
                      ? Icons.hourglass_top_rounded
                      : Icons.error_outline_rounded),
              color: statusColor,
              size: 20,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(cmd.action.toUpperCase(),
                    style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                        color: AppTheme.primary)),
                const SizedBox(height: 2),
                if (dt != null)
                  Text(
                    DateFormat('d MMM, HH:mm').format(dt),
                    style: TextStyle(
                        fontSize: 11, color: AppTheme.onSurfaceVariant),
                  ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(100),
              ),
              child: Text(
                cmd.status.toUpperCase(),
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1,
                  color: statusColor,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  DateTime? _parseDate(String raw) {
    try {
      return DateTime.parse(raw).toLocal();
    } catch (_) {
      return null;
    }
  }
}


