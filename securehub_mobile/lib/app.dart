import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/api/api_client.dart';
import 'core/auth/auth_notifier.dart';
import 'core/biometric/biometric_lock_service.dart';
import 'core/notifications/notification_service.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'shared/widgets/lock_screen.dart';

class ResponseApp extends ConsumerStatefulWidget {
  const ResponseApp({super.key});

  @override
  ConsumerState<ResponseApp> createState() => _ResponseAppState();
}

class _ResponseAppState extends ConsumerState<ResponseApp>
    with WidgetsBindingObserver {
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

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(appRouterProvider);
    final isLocked = ref.watch(appLockedProvider);

    // Navigate to site events when an alarm notification is tapped.
    ref.listen(notificationNavProvider, (_, siteId) {
      if (siteId != null) {
        router.go('/home/$siteId/events');
        ref.read(notificationNavProvider.notifier).clear();
      }
    });

    ref.listen(siteNotificationNavProvider, (_, siteId) {
      if (siteId != null) {
        router.go('/home/$siteId');
        ref.read(siteNotificationNavProvider.notifier).state = null;
      }
    });

    // Navigate to dedicated alarm alert screen when an alarm notification is tapped.
    ref.listen(criticalAlarmNavProvider, (_, navData) {
      if (navData != null) {
        final siteId = navData['site_id']!;
        final eventId = navData['event_id'];
        final query = eventId != null ? '?eventId=$eventId' : '';
        router.push('/alarm-alert/$siteId$query');
        ref.read(criticalAlarmNavProvider.notifier).clear();
      }
    });

    // Navigate to account-suspended screen when billing_lockout notification is tapped.
    ref.listen(billingLockoutNavProvider, (_, triggered) {
      if (triggered) {
        router.go('/account-suspended');
        ref.read(billingLockoutNavProvider.notifier).clear();
      }
    });

    // Navigate to messages inbox when a broadcast notification is tapped.
    ref.listen(messagesNavProvider, (_, triggered) {
      if (triggered) {
        router.go('/messages');
        ref.read(messagesNavProvider.notifier).clear();
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
