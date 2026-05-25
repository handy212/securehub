import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../features/messages/providers/messages_provider.dart';
import '../../features/sites/providers/selected_site_provider.dart';
import '../../features/sites/providers/sites_provider.dart';
import 'app_backdrop.dart';

class MainScaffold extends ConsumerWidget {
  const MainScaffold({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).matchedLocation;
    final selectedIndex = _getSelectedIndex(location);
    final header = _headerFor(location);
    final currentSiteId = ref.watch(currentSiteIdProvider);
    final selectedSiteName = ref.watch(
      siteListProvider.select(
        (sitesAsync) => sitesAsync.valueOrNull
            ?.where((site) => site.id == currentSiteId)
            .firstOrNull
            ?.name,
      ),
    );
    final siteSubtitle =
        location.startsWith('/home') && (selectedSiteName?.isNotEmpty ?? false)
        ? selectedSiteName!
        : header.subtitle;

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        backgroundColor: AppTheme.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        leadingWidth: 72,
        leading: Padding(
          padding: const EdgeInsets.only(left: 16),
          child: Center(
            child: Container(
              width: 46,
              height: 46,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.surfaceContainerLowest,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: AppTheme.outlineVariant.withValues(alpha: 0.14),
                ),
              ),
              child: Image.asset(
                'assets/images/Logo-WhiteBG.png',
                fit: BoxFit.contain,
              ),
            ),
          ),
        ),
        title: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              location.startsWith('/home') ? 'Secure Hub' : header.title,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.7,
                color: AppTheme.primary,
              ),
            ),
            if (siteSubtitle.isNotEmpty)
              Text(
                siteSubtitle,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
          ],
        ),
        actions: [
          const _NotificationBell(),
          if (location.startsWith('/home') && currentSiteId != null)
            _SiteRefreshButton(siteId: currentSiteId),
          if (location == '/messages')
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: () => ref.invalidate(inboxMessagesProvider),
              tooltip: 'Refresh',
            ),
          const SizedBox(width: 8),
        ],
      ),
      body: AppBackdrop(child: child),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: AppTheme.surfaceContainerLowest.withValues(alpha: 0.92),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          border: Border.all(
            color: AppTheme.outlineVariant.withValues(alpha: 0.10),
          ),
          boxShadow: [
            BoxShadow(
              color: AppTheme.onSurface.withValues(alpha: 0.03),
              blurRadius: 28,
              offset: const Offset(0, -8),
            ),
          ],
        ),
        child: SafeArea(
          child: SizedBox(
            height: 68,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _NavButton(
                  icon: Icons.dashboard_outlined,
                  activeIcon: Icons.dashboard_rounded,
                  label: 'Home',
                  isActive: selectedIndex == 0,
                  onTap: () {
                    HapticFeedback.selectionClick();
                    context.go('/home');
                  },
                ),
                _NavButton(
                  icon: Icons.grid_view_outlined,
                  activeIcon: Icons.grid_view_rounded,
                  label: 'Devices',
                  isActive: selectedIndex == 1,
                  onTap: () {
                    HapticFeedback.selectionClick();
                    context.go('/devices');
                  },
                ),
                _NavButton(
                  icon: Icons.history_rounded,
                  activeIcon: Icons.history_rounded,
                  label: 'Activity',
                  isActive: selectedIndex == 2,
                  onTap: () {
                    HapticFeedback.selectionClick();
                    context.go('/activities');
                  },
                ),
                _NavButton(
                  icon: Icons.manage_accounts_outlined,
                  activeIcon: Icons.manage_accounts_rounded,
                  label: 'Account',
                  isActive: selectedIndex == 3,
                  onTap: () {
                    HapticFeedback.selectionClick();
                    context.go('/menu');
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  int _getSelectedIndex(String location) {
    if (location.startsWith('/home')) return 0;
    if (location.startsWith('/devices')) return 1;
    if (location.startsWith('/activities')) return 2;
    if (location.startsWith('/menu') || location.startsWith('/messages')) {
      return 3;
    }
    return 0;
  }

  _ScaffoldHeader _headerFor(String location) {
    if (location.startsWith('/devices')) {
      return const _ScaffoldHeader('Devices', 'Sensors, hubs and health');
    }
    if (location.startsWith('/activities')) {
      return const _ScaffoldHeader('Activity', 'Recent events and actions');
    }
    if (location.startsWith('/menu')) {
      return const _ScaffoldHeader('Account', 'Settings and support');
    }
    if (location.startsWith('/messages')) {
      return const _ScaffoldHeader('Inbox', 'Provider updates and alerts');
    }
    return const _ScaffoldHeader('Secure Hub', '');
  }
}

class _ScaffoldHeader {
  const _ScaffoldHeader(this.title, this.subtitle);

  final String title;
  final String subtitle;
}

class _NotificationBell extends ConsumerWidget {
  const _NotificationBell();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final messagesAsync = ref.watch(inboxMessagesProvider);

    return messagesAsync.when(
      data: (messages) => IconButton(
        onPressed: () {
          HapticFeedback.lightImpact();
          context.push('/messages');
        },
        style: IconButton.styleFrom(
          backgroundColor: AppTheme.surfaceContainerLow,
          foregroundColor: AppTheme.primary,
          minimumSize: const Size(42, 42),
        ),
        tooltip: 'Inbox',
        icon: Icon(
          messages.isEmpty
              ? Icons.notifications_none_rounded
              : Icons.mark_email_unread_rounded,
        ),
      ),
      loading: () => IconButton(
        onPressed: null,
        style: IconButton.styleFrom(
          backgroundColor: AppTheme.surfaceContainerLow,
          foregroundColor: AppTheme.primary,
          minimumSize: const Size(42, 42),
        ),
        icon: const SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      ),
      error: (_, _) => IconButton(
        onPressed: () => context.push('/messages'),
        style: IconButton.styleFrom(
          backgroundColor: AppTheme.surfaceContainerLow,
          foregroundColor: AppTheme.primary,
          minimumSize: const Size(42, 42),
        ),
        icon: const Icon(Icons.notifications_none_rounded),
      ),
    );
  }
}

class _SiteRefreshButton extends ConsumerWidget {
  const _SiteRefreshButton({required this.siteId});

  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final refreshState = ref.watch(hardwareRefreshProvider(siteId));

    return IconButton(
      onPressed: refreshState.isLoading
          ? null
          : () => ref.read(hardwareRefreshProvider(siteId).notifier).refresh(),
      style: IconButton.styleFrom(
        backgroundColor: AppTheme.surfaceContainerLow,
        foregroundColor: AppTheme.primary,
        minimumSize: const Size(42, 42),
      ),
      tooltip: 'Refresh site status',
      icon: refreshState.isLoading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.sync_rounded),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  final IconData icon;
  final IconData activeIcon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isActive ? AppTheme.surfaceContainerLow : Colors.transparent,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isActive ? activeIcon : icon,
              color: isActive
                  ? AppTheme.primary
                  : AppTheme.onSurfaceVariant.withValues(alpha: 0.65),
              size: 24,
            ),
            AnimatedSize(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              child: isActive
                  ? Padding(
                      padding: const EdgeInsets.only(left: 8),
                      child: Text(
                        label,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.primary,
                        ),
                      ),
                    )
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    );
  }
}

