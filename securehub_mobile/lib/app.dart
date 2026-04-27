import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/api/api_client.dart';
import 'core/auth/auth_notifier.dart';
import 'core/biometric/biometric_lock_service.dart';
import 'core/notifications/notification_service.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/sites/providers/selected_site_provider.dart';
import 'features/sites/providers/sites_provider.dart';
import 'shared/widgets/lock_screen.dart';

class ResponseApp extends ConsumerStatefulWidget {
  const ResponseApp({super.key});

  @override
  ConsumerState<ResponseApp> createState() => _ResponseAppState();
}

class _ResponseAppState extends ConsumerState<ResponseApp>
    with WidgetsBindingObserver {
  String? _activeAlarmRouteKey;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Initialize push notifications (no-ops if Firebase is not configured).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(notificationServiceProvider).initialize();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    final lockSvc = ref.read(biometricLockServiceProvider);
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      lockSvc.onBackground();
    } else if (state == AppLifecycleState.resumed) {
      lockSvc.onResume();
    }
  }

  void _showAlarmAlert(
    GoRouter router, {
    required String siteId,
    String? eventId,
  }) {
    final alarmKey = '$siteId:${eventId ?? ''}';
    final currentPath = router.routeInformationProvider.value.uri.path;

    if (_activeAlarmRouteKey == alarmKey ||
        currentPath.startsWith('/alarm-alert/')) {
      return;
    }

    _activeAlarmRouteKey = alarmKey;
    final alertLocation = Uri(
      path: '/alarm-alert/$siteId',
      queryParameters: eventId == null ? null : {'eventId': eventId},
    ).toString();
    router.push(alertLocation).whenComplete(() {
      if (mounted && _activeAlarmRouteKey == alarmKey) {
        _activeAlarmRouteKey = null;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(appRouterProvider);
    final isLocked = ref.watch(appLockedProvider);

    // Navigate to site events when an alarm notification is tapped.
    ref.listen(notificationNavProvider, (_, siteId) {
      if (siteId != null) {
        Future.microtask(() {
          router.go('/home/$siteId/events');
          ref.read(notificationNavProvider.notifier).clear();
        });
      }
    });

    ref.listen(siteNotificationNavProvider, (_, siteId) {
      if (siteId != null) {
        Future.microtask(() {
          router.go('/home/$siteId');
          ref.read(siteNotificationNavProvider.notifier).state = null;
        });
      }
    });

    // Navigate to dedicated alarm alert screen when an alarm notification is tapped.
    ref.listen(criticalAlarmNavProvider, (_, navData) {
      if (navData != null) {
        final siteId = navData['site_id']!;
        final eventId = navData['event_id'];
        Future.microtask(() {
          _showAlarmAlert(router, siteId: siteId, eventId: eventId);
          ref.read(criticalAlarmNavProvider.notifier).clear();
        });
      }
    });

    // Navigate to account-suspended screen when billing_lockout notification is tapped.
    ref.listen(billingLockoutNavProvider, (_, triggered) {
      if (triggered) {
        Future.microtask(() {
          router.go('/account-suspended');
          ref.read(billingLockoutNavProvider.notifier).clear();
        });
      }
    });

    // Navigate to messages inbox when a broadcast notification is tapped.
    ref.listen(messagesNavProvider, (_, triggered) {
      if (triggered) {
        Future.microtask(() {
          router.go('/messages');
          ref.read(messagesNavProvider.notifier).clear();
        });
      }
    });

    ref.listen(forceLogoutProvider, (_, shouldLogout) {
      if (shouldLogout) {
        ref.read(forceLogoutProvider.notifier).reset();
        Future.microtask(() {
          ref.read(authNotifierProvider.notifier).logout();
        });
      }
    });

    // Automatically show alarm alert when an active alarm is detected via polling
    final currentSiteId = ref.watch(currentSiteIdProvider);
    if (currentSiteId != null) {
      ref.listen(sitePollProvider(currentSiteId), (prev, next) {
        final poll = next.valueOrNull;
        if (poll != null && poll.activeAlarmCount > 0) {
          // Check if we are already on the alarm alert screen to avoid duplicates
          // Use a more robust check for the current route
          final location = router.routeInformationProvider.value.uri.path;
          if (!location.startsWith('/alarm-alert/')) {
            final eventId = poll.lastEvent?.id;

            if (kDebugMode) {
              debugPrint(
                'ALARM DETECTED for $currentSiteId. Triggering overlay.',
              );
            }

            Future.microtask(() {
              _showAlarmAlert(router, siteId: poll.siteId, eventId: eventId);
            });
          }
        }
      });
    }

    return MaterialApp.router(
      title: 'Secure Hub',
      routerConfig: router,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      builder: (context, child) {
        return Stack(
          children: [
            child ?? const SizedBox.shrink(),
            if (isLocked) const LockScreen(),
          ],
        );
      },
    );
  }
}
