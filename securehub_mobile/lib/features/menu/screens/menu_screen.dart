import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/auth/auth_notifier.dart';
import '../../../core/theme/app_theme.dart';
import '../../emergency/widgets/emergency_action_card.dart';

class MenuScreen extends ConsumerWidget {
  const MenuScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final profile = authState is AuthAuthenticated ? authState.profile : null;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: CustomScrollView(
        slivers: [
          // ── Profile section ──────────────────────────────────────────────
          if (profile != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                child: Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceContainerLowest,
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: AppTheme.cardShadow,
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 64,
                        height: 64,
                        decoration: const BoxDecoration(
                          color: AppTheme.primary,
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: Text(
                            (profile.user.firstName.isNotEmpty
                                    ? profile.user.firstName[0]
                                    : (profile.user.username.isNotEmpty
                                          ? profile.user.username[0]
                                          : '?'))
                                .toUpperCase(),
                            style: TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.w800,
                              color: AppTheme.onPrimary,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 20),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              profile.user.firstName.isNotEmpty
                                  ? '${profile.user.firstName} ${profile.user.lastName}'
                                  : profile.user.username,
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 18,
                                color: AppTheme.primary,
                              ),
                            ),
                            const SizedBox(height: 4),
                            if (profile.user.email.isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Text(
                                profile.user.email,
                                style: TextStyle(
                                  color: AppTheme.onSurfaceVariant,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(
                          Icons.edit_outlined,
                          color: AppTheme.outlineVariant,
                        ),
                        onPressed: () => context.push('/menu/profile'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: EmergencyActionCard(triggerContext: 'away'),
            ),
          ),

          // ── Menu sections ────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Column(
              children: [
                _MenuSection(
                  title: 'Preferences',
                  children: [
                    _MenuTile(
                      icon: Icons.manage_accounts_outlined,
                      label: 'Account & security',
                      onTap: () => context.push('/menu/profile'),
                    ),
                    _MenuTile(
                      icon: Icons.notifications_none_rounded,
                      label: 'Notifications',
                      onTap: () => context.push('/menu/notifications'),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _MenuSection(
                  title: 'Help',
                  children: [
                    _MenuTile(
                      icon: Icons.mail_outline_rounded,
                      label: 'Inbox',
                      onTap: () => context.push('/messages'),
                    ),
                    _MenuTile(
                      icon: Icons.help_outline_rounded,
                      label: 'Support',
                      onTap: () => context.push('/menu/help'),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // ── Sign out ─────────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
              child: Material(
                color: AppTheme.error.withValues(alpha: 0.04),
                borderRadius: BorderRadius.circular(20),
                clipBehavior: Clip.antiAlias,
                child: Container(
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: AppTheme.error.withValues(alpha: 0.1),
                    ),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 4,
                    ),
                    leading: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.error.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(
                        Icons.logout_rounded,
                        color: AppTheme.error,
                        size: 18,
                      ),
                    ),
                    title: Text(
                      'Sign out',
                      style: TextStyle(
                        color: AppTheme.error,
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                      ),
                    ),
                    trailing: const Icon(
                      Icons.chevron_right_rounded,
                      color: AppTheme.error,
                      size: 20,
                    ),
                    onTap: () async {
                      HapticFeedback.mediumImpact();
                      final confirmed = await showDialog<bool>(
                        context: context,
                        barrierColor: AppTheme.primary.withValues(alpha: 0.4),
                        builder: (ctx) => AlertDialog(
                          backgroundColor: AppTheme.surfaceContainerLowest,
                          surfaceTintColor: Colors.transparent,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(28),
                          ),
                          title: Text(
                            'Sign Out',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              color: AppTheme.primary,
                              letterSpacing: -0.5,
                            ),
                          ),
                          content: Text(
                            'Are you sure you want to sign out on this device?',
                            style: TextStyle(
                              color: AppTheme.onSurfaceVariant,
                              fontSize: 14,
                              height: 1.4,
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(ctx).pop(false),
                              child: Text(
                                'CANCEL',
                                style: TextStyle(
                                  color: AppTheme.onSurfaceVariant,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            FilledButton(
                              onPressed: () {
                                HapticFeedback.mediumImpact();
                                Navigator.of(ctx).pop(true);
                              },
                              style: FilledButton.styleFrom(
                                backgroundColor: AppTheme.error,
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 24,
                                  vertical: 12,
                                ),
                              ),
                              child: const Text('SIGN OUT'),
                            ),
                          ],
                        ),
                      );
                      if (confirmed == true && context.mounted) {
                        await ref.read(authNotifierProvider.notifier).logout();
                      }
                    },
                  ),
                ),
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 120)),
        ],
      ),
    );
  }
}

class _MenuSection extends StatelessWidget {
  const _MenuSection({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          child: Text(
            title.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
              color: AppTheme.onSurfaceVariant,
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Material(
            color: AppTheme.surfaceContainerLow,
            borderRadius: const BorderRadius.all(Radius.circular(20)),
            clipBehavior: Clip.antiAlias,
            child: Column(children: children),
          ),
        ),
      ],
    );
  }
}

class _MenuTile extends StatelessWidget {
  const _MenuTile({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppTheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: AppTheme.primary, size: 18),
        ),
        title: Text(
          label,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 14,
            color: AppTheme.primary,
          ),
        ),
        trailing: const Icon(
          Icons.chevron_right_rounded,
          size: 20,
          color: AppTheme.outlineVariant,
        ),
        onTap: onTap,
      ),
    );
  }
}

