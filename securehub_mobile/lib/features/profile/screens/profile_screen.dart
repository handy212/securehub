import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/biometric/biometric_lock_service.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../../sites/providers/sites_provider.dart';
import '../../sites/providers/selected_site_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final profile = authState is AuthAuthenticated ? authState.profile : null;

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: Text(
          'Profile',
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 17,
            letterSpacing: -0.5,
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        children: [
          // Header / Avatar
          Center(
            child: Column(
              children: [
                Container(
                  width: 92,
                  height: 92,
                  decoration: BoxDecoration(
                    color: AppTheme.primary,
                    shape: BoxShape.circle,
                    boxShadow: AppTheme.cardShadow,
                    border: Border.all(
                      color: AppTheme.surfaceContainerLowest,
                      width: 4,
                    ),
                  ),
                  child: Center(
                    child: Text(
                      _initials(
                        profile?.user.firstName,
                        profile?.user.lastName,
                        profile?.user.username,
                      ),
                      style: TextStyle(
                        fontSize: 32,
                        color: AppTheme.onPrimary,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                if (profile != null) ...[
                  Text(
                    '${profile.user.firstName} ${profile.user.lastName}'
                            .trim()
                            .isNotEmpty
                        ? '${profile.user.firstName} ${profile.user.lastName}'
                              .trim()
                        : profile.user.username,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                      color: AppTheme.primary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '@${profile.user.username}',
                    style: TextStyle(
                      color: AppTheme.onSurfaceVariant,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 16),
                  // Subscription Badge
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: AppTheme.secondary.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(100),
                      border: Border.all(
                        color: AppTheme.secondary.withValues(alpha: 0.1),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.verified_user_rounded,
                          size: 14,
                          color: AppTheme.secondary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'MONITORED ACCOUNT',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 1.2,
                            color: AppTheme.secondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(height: 48),

          // Info Section
          if (profile != null) ...[
            _ProfileSection(
              title: 'Contact details',
              children: [
                _InfoTile(
                  icon: Icons.email_outlined,
                  label: 'Email address',
                  value: profile.user.email.isNotEmpty
                      ? profile.user.email
                      : 'Not provided',
                ),
                _InfoTile(
                  icon: Icons.phone_outlined,
                  label: 'Phone number',
                  value: profile.phoneNumber.isNotEmpty
                      ? profile.phoneNumber
                      : 'Not provided',
                ),
              ],
            ),
            const SizedBox(height: 32),
          ],

          const _BiometricTile(),
          const SizedBox(height: 32),

          const _SiteSection(),

          const SizedBox(height: 48),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
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
                  onTap: () {
                    HapticFeedback.mediumImpact();
                    _showLogoutDialog(context, ref);
                  },
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.error.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.logout_rounded,
                      color: AppTheme.error,
                      size: 20,
                    ),
                  ),
                  title: Text(
                    'Sign out of session',
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
                ),
              ),
            ),
          ),

          const SizedBox(height: 120),
        ],
      ),
    );
  }

  void _showLogoutDialog(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      barrierColor: AppTheme.primary.withValues(alpha: 0.4),
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppTheme.surfaceContainerLowest,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
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
            onPressed: () => Navigator.of(dialogContext).pop(false),
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
              Navigator.of(dialogContext).pop(true);
            },
            style: FilledButton.styleFrom(
              backgroundColor: AppTheme.error,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
            child: const Text('SIGN OUT'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await ref.read(authNotifierProvider.notifier).logout();
    }
  }

  String _initials(String? first, String? last, String? username) {
    if ((first?.isNotEmpty ?? false) || (last?.isNotEmpty ?? false)) {
      return '${first?.isNotEmpty == true ? first![0] : ''}${last?.isNotEmpty == true ? last![0] : ''}'
          .toUpperCase();
    }
    return username?.substring(0, 1).toUpperCase() ?? '?';
  }
}

class _BiometricTile extends ConsumerStatefulWidget {
  const _BiometricTile();

  @override
  ConsumerState<_BiometricTile> createState() => _BiometricTileState();
}

class _BiometricTileState extends ConsumerState<_BiometricTile> {
  bool? _enabled;
  bool _available = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final svc = ref.read(biometricLockServiceProvider);
    final available = await svc.isAvailable();
    final enabled = await svc.isEnabled();
    if (mounted) {
      setState(() {
        _available = available;
        _enabled = enabled;
      });
    }
  }

  Future<void> _toggleBiometric(bool enabled) async {
    if (_saving) return;

    setState(() => _saving = true);
    final svc = ref.read(biometricLockServiceProvider);

    try {
      if (enabled) {
        final authenticated = await svc.authenticate();
        if (!authenticated) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Identity verification was cancelled or failed.'),
              ),
            );
          }
          return;
        }
      }

      await svc.setEnabled(enabled: enabled);
      if (mounted) {
        setState(() => _enabled = enabled);
      }
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 12),
          child: Text(
            'APP SECURITY',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
              color: AppTheme.onSurfaceVariant,
            ),
          ),
        ),
        Material(
          color: AppTheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(20),
          clipBehavior: Clip.antiAlias,
          child: SwitchListTile(
            secondary: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.surfaceContainerLowest,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(
                Icons.fingerprint_rounded,
                color: AppTheme.primary,
                size: 20,
              ),
            ),
            title: Text(
              'Identity verification',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
            ),
            subtitle: Text(
              _available
                  ? 'Require Face ID or fingerprint to reopen the app'
                  : 'Require Face ID or fingerprint to reopen the app.',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.onSurfaceVariant,
              ),
            ),
            value: _enabled ?? false,
            activeThumbColor: AppTheme.secondary,
            activeTrackColor: AppTheme.secondary.withValues(alpha: 0.35),
            onChanged: _enabled == null || _saving
                ? null
                : (val) async {
                    HapticFeedback.lightImpact();
                    await _toggleBiometric(val);
                  },
          ),
        ),
      ],
    );
  }
}

class _SiteSection extends ConsumerWidget {
  const _SiteSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sitesAsync = ref.watch(siteListProvider);
    final selectedId = ref.watch(currentSiteIdProvider);

    return sitesAsync.when(
      data: (sites) {
        if (sites.isEmpty) return const SizedBox.shrink();

        final selectedSite = sites.firstWhere(
          (s) => s.id == selectedId,
          orElse: () => sites.first,
        );

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(left: 4, bottom: 12),
              child: Text(
                'ACTIVE SITE',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.5,
                  color: AppTheme.onSurfaceVariant,
                ),
              ),
            ),
            Material(
              color: AppTheme.surfaceContainerLow,
              borderRadius: BorderRadius.circular(20),
              clipBehavior: Clip.antiAlias,
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 4,
                ),
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceContainerLowest,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.business_rounded,
                    color: AppTheme.primary,
                    size: 20,
                  ),
                ),
                title: Text(
                  selectedSite.name,
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
                subtitle: Text(
                  selectedSite.city.isNotEmpty
                      ? selectedSite.city
                      : 'Authorized Hub',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppTheme.onSurfaceVariant,
                  ),
                ),
                trailing: sites.length > 1
                    ? const Icon(
                        Icons.swap_horiz_rounded,
                        color: AppTheme.outlineVariant,
                      )
                    : null,
                onTap: sites.length > 1
                    ? () {
                        HapticFeedback.lightImpact();
                        _showSitePicker(context, ref, sites, selectedId);
                      }
                    : null,
              ),
            ),
          ],
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, _) => const SizedBox.shrink(),
    );
  }

  void _showSitePicker(
    BuildContext context,
    WidgetRef ref,
    List<Site> sites,
    String? currentId,
  ) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          decoration: const BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
          ),
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.outlineVariant.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 32),
              Text(
                'SWITCH ACTIVE SITE',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.5,
                  color: AppTheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 16),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: sites.length,
                  itemBuilder: (context, i) {
                    final site = sites[i];
                    final isSelected = site.id == currentId;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Material(
                        color: isSelected
                            ? AppTheme.primary.withValues(alpha: 0.04)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(16),
                        clipBehavior: Clip.antiAlias,
                        child: Container(
                          decoration: BoxDecoration(
                            border: Border.all(
                              color: isSelected
                                  ? AppTheme.primary.withValues(alpha: 0.1)
                                  : Colors.transparent,
                            ),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: GestureDetector(
                            onTapDown: (_) => HapticFeedback.selectionClick(),
                            child: ListTile(
                              leading: Icon(
                                Icons.business_rounded,
                                color: isSelected
                                    ? AppTheme.primary
                                    : AppTheme.outlineVariant,
                              ),
                              title: Text(
                                site.name,
                                style: TextStyle(
                                  fontWeight: isSelected
                                      ? FontWeight.w700
                                      : FontWeight.w500,
                                  color: isSelected
                                      ? AppTheme.primary
                                      : AppTheme.onSurface,
                                ),
                              ),
                              trailing: isSelected
                                  ? const Icon(
                                      Icons.check_circle_rounded,
                                      color: AppTheme.secondary,
                                    )
                                  : null,
                              onTap: () {
                                HapticFeedback.mediumImpact();
                                ref
                                    .read(selectedSiteProvider.notifier)
                                    .select(site.id);
                                Navigator.pop(context);
                              },
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ProfileSection extends StatelessWidget {
  const _ProfileSection({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 12),
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
        Material(
          color: AppTheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(20),
          clipBehavior: Clip.antiAlias,
          child: Column(children: children),
        ),
      ],
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppTheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: AppTheme.primary, size: 20),
        ),
        title: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: AppTheme.onSurfaceVariant,
            letterSpacing: 0.2,
          ),
        ),
        subtitle: Text(
          value,
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            color: AppTheme.primary,
            letterSpacing: -0.2,
          ),
        ),
      ),
    );
  }
}

