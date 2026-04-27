import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/emergency_provider.dart';

class EmergencyActionCard extends ConsumerWidget {
  const EmergencyActionCard({
    super.key,
    this.site,
    required this.triggerContext,
  });

  final Site? site;
  final String triggerContext;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusAsync = ref.watch(emergencyStatusProvider(site?.id));
    final emergencyState = ref.watch(emergencyControllerProvider);

    return statusAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, _) => const SizedBox.shrink(),
      data: (status) {
        if (!status.enabled) return const SizedBox.shrink();

        final active = emergencyState.activeRequest;
        final activeForThisCard =
            active != null &&
            (site == null ? active.siteId == null : active.siteId == site!.id);
        final hasOtherActive =
            emergencyState.hasActiveRequest && !activeForThisCard;

        return _EmergencyShell(
          isActive: activeForThisCard,
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: activeForThisCard
                      ? Colors.white.withValues(alpha: 0.16)
                      : AppTheme.error.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  activeForThisCard
                      ? Icons.location_searching_rounded
                      : Icons.emergency_share_rounded,
                  color: activeForThisCard ? Colors.white : AppTheme.error,
                  size: 22,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      activeForThisCard
                          ? 'Patrol request sent'
                          : 'Emergency patrol',
                      style: GoogleFonts.inter(
                        color: activeForThisCard
                            ? Colors.white
                            : AppTheme.primary,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      activeForThisCard
                          ? 'Live GPS is updating dispatch'
                          : (site == null
                                ? 'Send away-from-site GPS'
                                : 'Send site and GPS to dispatch'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: activeForThisCard
                            ? Colors.white.withValues(alpha: 0.76)
                            : AppTheme.onSurfaceVariant,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              if (activeForThisCard)
                _EmergencyButton(
                  label: emergencyState.isCancelling ? '...' : 'Cancel',
                  foreground: AppTheme.error,
                  background: Colors.white,
                  onPressed: emergencyState.isCancelling
                      ? null
                      : () => _cancel(context, ref),
                )
              else
                _EmergencyButton(
                  label: emergencyState.isSending ? '...' : 'Send',
                  foreground: Colors.white,
                  background: hasOtherActive
                      ? AppTheme.outlineVariant
                      : AppTheme.error,
                  onPressed: emergencyState.isSending || hasOtherActive
                      ? null
                      : () => _confirmAndTrigger(context, ref),
                ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _confirmAndTrigger(BuildContext context, WidgetRef ref) async {
    HapticFeedback.mediumImpact();
    final confirmed = await showDialog<bool>(
      context: context,
      barrierColor: AppTheme.primary.withValues(alpha: 0.42),
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppTheme.surfaceContainerLowest,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: Text(
          'Send Emergency Request?',
          style: GoogleFonts.inter(
            fontWeight: FontWeight.w800,
            color: AppTheme.primary,
          ),
        ),
        content: Text(
          'SecureHub will share your GPS location with dispatch and keep updating it until the request is cancelled or resolved.',
          style: GoogleFonts.inter(
            color: AppTheme.onSurfaceVariant,
            height: 1.4,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppTheme.error),
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Send'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;

    final authState = ref.read(authNotifierProvider);
    final phone = authState is AuthAuthenticated
        ? authState.profile.phoneNumber
        : null;
    try {
      await ref
          .read(emergencyControllerProvider.notifier)
          .trigger(
            siteId: site?.id,
            triggerContext: triggerContext,
            contactPhone: phone,
            note: site == null ? 'Away from site emergency request' : null,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Emergency request sent.')),
        );
      }
    } catch (_) {
      if (context.mounted) _showError(context, ref);
    }
  }

  Future<void> _cancel(BuildContext context, WidgetRef ref) async {
    HapticFeedback.lightImpact();
    try {
      await ref.read(emergencyControllerProvider.notifier).cancel();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Emergency request cancelled.')),
        );
      }
    } catch (_) {
      if (context.mounted) _showError(context, ref);
    }
  }

  void _showError(BuildContext context, WidgetRef ref) {
    final message =
        ref.read(emergencyControllerProvider).lastError ??
        'Unable to send emergency request.';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: AppTheme.error),
    );
    ref.read(emergencyControllerProvider.notifier).clearError();
  }
}

class _EmergencyShell extends StatelessWidget {
  const _EmergencyShell({required this.child, this.isActive = false});

  final Widget child;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isActive ? AppTheme.error : AppTheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isActive
              ? AppTheme.error.withValues(alpha: 0.20)
              : AppTheme.error.withValues(alpha: 0.10),
        ),
        boxShadow: AppTheme.cardShadow,
      ),
      child: child,
    );
  }
}

class _EmergencyButton extends StatelessWidget {
  const _EmergencyButton({
    required this.label,
    required this.foreground,
    required this.background,
    required this.onPressed,
  });

  final String label;
  final Color foreground;
  final Color background;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: onPressed,
      style: FilledButton.styleFrom(
        minimumSize: const Size(70, 38),
        padding: const EdgeInsets.symmetric(horizontal: 12),
        backgroundColor: background,
        foregroundColor: foreground,
        disabledBackgroundColor: background.withValues(alpha: 0.6),
        disabledForegroundColor: foreground.withValues(alpha: 0.6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w900),
      ),
    );
  }
}
