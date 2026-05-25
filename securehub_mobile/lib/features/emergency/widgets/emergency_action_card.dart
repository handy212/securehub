import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/auth/auth_notifier.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/emergency_provider.dart';
import 'emergency_request_dialog.dart';

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
                          ? 'Emergency Request Sent'
                          : 'Emergency Request',
                      style: TextStyle(
                        color: activeForThisCard
                            ? Colors.white
                            : AppTheme.primary,
                        fontSize: 14,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.2,
                      ),
                    ),
                    if (activeForThisCard) ...[
                      const SizedBox(height: 2),
                      Text(
                        'Live GPS is updating dispatch',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.76),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 10),
              if (activeForThisCard)
                _EmergencyButton(
                  label: emergencyState.isCancelling ? '...' : 'CANCEL',
                  foreground: AppTheme.error,
                  background: Colors.white,
                  onPressed: emergencyState.isCancelling
                      ? null
                      : () => _cancel(context, ref),
                )
              else
                _EmergencyButton(
                  label: emergencyState.isSending ? '...' : 'TRIGGER',
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
    final confirmed = await EmergencyRequestDialog.show(context);

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
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900),
      ),
    );
  }
}

