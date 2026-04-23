import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_surfaces.dart';
import '../providers/messages_provider.dart';

class MessagesScreen extends ConsumerWidget {
  const MessagesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final messagesAsync = ref.watch(inboxMessagesProvider);

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 16),
            child: AppPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const AppSectionHeader(
                    eyebrow: 'Communications',
                    title: 'Inbox',
                    subtitle:
                        'Provider notices, billing updates, and operational alerts in one queue.',
                  ),
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      AppMetricChip(
                        label: 'Messages',
                        value: messagesAsync.valueOrNull?.length.toString() ?? '--',
                        tone: AppTheme.primary,
                      ),
                      AppMetricChip(
                        label: 'Billing',
                        value: '${messagesAsync.valueOrNull?.where((m) => m.messageType == 'billing').length ?? 0}',
                        tone: AppTheme.onTertiaryContainer,
                      ),
                      AppMetricChip(
                        label: 'Alerts',
                        value: '${messagesAsync.valueOrNull?.where((m) => m.messageType == 'alert').length ?? 0}',
                        tone: AppTheme.error,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
        messagesAsync.when(
          loading: () => const SliverFillRemaining(
            hasScrollBody: false,
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (err, _) => SliverFillRemaining(
            hasScrollBody: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: AppErrorState(
                title: 'Could not load inbox',
                message: 'Check your connection and try again.',
                action: FilledButton(
                  onPressed: () => ref.invalidate(inboxMessagesProvider),
                  child: const Text('Retry'),
                ),
              ),
            ),
          ),
          data: (messages) {
            if (messages.isEmpty) {
              return const SliverFillRemaining(
                hasScrollBody: false,
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: AppEmptyState(
                    icon: Icons.mark_chat_read_rounded,
                    title: 'Inbox Clear',
                    message:
                        'New account, billing, and service messages will appear here as they arrive.',
                  ),
                ),
              );
            }
            return SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 120),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, i) => _MessageCard(message: messages[i]),
                  childCount: messages.length,
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _MessageCard extends ConsumerWidget {
  const _MessageCard({required this.message, super.key});
  final InboxMessage message;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = _typeConfig(message.messageType);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          onTap: () {
            HapticFeedback.lightImpact();
            _showMessageDetails(context, config, ref);
          },
          child: Stack(
            children: [
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                child: Container(
                  width: 5,
                  color: config.barColor,
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 16, 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: config.barColor.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Icon(
                            config.icon,
                            size: 16,
                            color: config.barColor,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            message.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                              color: AppTheme.onSurface,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: config.barColor.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(100),
                          ),
                          child: Text(
                            config.label,
                            style: GoogleFonts.inter(
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1,
                              color: config.barColor,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        const Icon(
                          Icons.schedule_rounded,
                          size: 11,
                          color: AppTheme.outline,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _formatDate(message.createdAt),
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            color: AppTheme.outline,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const Spacer(),
                        Text(
                          'Open Message',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            color: config.barColor,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          Icons.arrow_forward_ios_rounded,
                          size: 10,
                          color: config.barColor,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showMessageDetails(BuildContext context, _TypeConfig config, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        titlePadding: EdgeInsets.zero,
        contentPadding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
        title: Column(
          children: [
            Align(
              alignment: Alignment.topRight,
              child: IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: () => Navigator.pop(context),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: config.barColor.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(config.icon, color: config.barColor, size: 28),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    message.title,
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      fontWeight: FontWeight.w800,
                      fontSize: 18,
                      color: AppTheme.onSurface,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: config.barColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(100),
                    ),
                    child: Text(
                      config.label,
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        color: config.barColor,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            const Divider(height: 1),
          ],
        ),
        content: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.4,
          ),
          child: SingleChildScrollView(
            padding: const EdgeInsets.only(top: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  message.body,
                  style: GoogleFonts.inter(
                    fontSize: 15,
                    height: 1.6,
                    color: AppTheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    const Icon(
                      Icons.schedule_rounded,
                      size: 14,
                      color: AppTheme.outline,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _formatDate(message.createdAt),
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppTheme.outline,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Close',
              style: GoogleFonts.inter(
                fontWeight: FontWeight.w700,
                color: AppTheme.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'Yesterday';
    return DateFormat('d MMM, HH:mm').format(dt);
  }

  _TypeConfig _typeConfig(String type) {
    switch (type) {
      case 'billing':
        return const _TypeConfig(
          icon: Icons.account_balance_wallet_rounded,
          barColor: AppTheme.onTertiaryContainer,
          label: 'BILLING',
        );
      case 'alert':
        return const _TypeConfig(
          icon: Icons.gpp_maybe_rounded,
          barColor: AppTheme.error,
          label: 'ALERT',
        );
      default:
        return const _TypeConfig(
          icon: Icons.forum_rounded,
          barColor: AppTheme.secondary,
          label: 'SYSTEM',
        );
    }
  }
}

class _TypeConfig {
  const _TypeConfig({
    required this.icon,
    required this.barColor,
    required this.label,
  });
  final IconData icon;
  final Color barColor;
  final String label;
}
