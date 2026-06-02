import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../api/exceptions.dart';
import '../auth/auth_notifier.dart';
import '../../features/alarms/screens/alarm_alert_screen.dart';
import '../../features/auth/screens/account_suspended_screen.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/messages/screens/messages_screen.dart';
import '../../features/sites/screens/site_detail_screen.dart';
import '../../features/sites/screens/site_suspended_screen.dart';
import '../../features/alarms/screens/event_list_screen.dart';
import '../../features/alarms/screens/command_history_screen.dart';
import '../../features/sites/screens/camera_live_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/devices/screens/device_list_screen.dart';
import '../../features/activities/screens/activities_screen.dart';
import '../../features/client_guarding/screens/client_guarding_screen.dart';
import '../../features/menu/screens/menu_screen.dart';
import '../../features/profile/screens/notification_settings_screen.dart';
import '../../features/profile/screens/help_screen.dart';
import '../../features/guard/models/guard_models.dart';
import '../../features/guard/screens/guard_home_screen.dart';
import '../../features/guard/screens/shift_detail_screen.dart';
import '../../features/guard/screens/guard_patrol_screen.dart';
import '../../features/guard/screens/guard_dispatch_screen.dart';
import '../../features/guard/screens/guard_panic_screen.dart';
import '../../features/guard/screens/guard_patrol_scan_screen.dart';
import '../../features/guard/screens/guard_report_screen.dart';
import '../../features/guard/screens/guard_welfare_screen.dart';
import '../../features/sites/providers/selected_site_provider.dart';
import '../../features/sites/providers/sites_provider.dart';
import '../../shared/widgets/main_scaffold.dart';

part 'app_router.g.dart';

final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<NavigatorState> shellNavigatorKey = GlobalKey<NavigatorState>();

@riverpod
Listenable authRefreshListenable(Ref ref) {
  final notifier = ValueNotifier(0);
  ref.listen(authNotifierProvider, (_, _) => notifier.value++);
  ref.listen(selectedSiteProvider, (_, _) => notifier.value++);
  // Also listen to site list errors for suspension detection
  ref.listen(siteListProvider, (_, _) => notifier.value++);
  ref.keepAlive();
  return notifier;
}

@riverpod
GoRouter appRouter(Ref ref) {
  final authRefresh = ref.read(authRefreshListenableProvider);

  return GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/home',
    refreshListenable: authRefresh,
    redirect: (context, state) {
      final authState = ref.read(authNotifierProvider);
      final isLoading = authState is AuthLoading;
      final authenticated = authState is AuthAuthenticated ? authState : null;
      final isAuthenticated = authenticated != null;

      final isLoginRoute = state.matchedLocation == '/login';
      final isLoadingRoute = state.matchedLocation == '/loading';

      if (isLoading && !isLoadingRoute && !isLoginRoute) return '/loading';
      if (!isLoading && !isAuthenticated && !isLoginRoute) return '/login';
      if (authenticated != null && (isLoginRoute || isLoadingRoute)) {
        return authenticated.isGuard ? '/guard/home' : '/home';
      }

      final isGuard = authenticated?.isGuard ?? false;
      final hasGuardingClientAccess =
          authenticated?.session.hasGuardingClientAccess ?? false;

      // Global Account Suspension Check (customer accounts only)
      if (isAuthenticated && !isGuard) {
        final sitesAsync = ref.read(siteListProvider);
        final isSuspended = sitesAsync.maybeWhen(
          error: (err, _) =>
              err is AccountSuspendedException ||
              err.toString().contains('AccountSuspendedException'),
          orElse: () => false,
        );

        if (isSuspended) {
          if (state.matchedLocation != '/account-suspended') {
            return '/account-suspended';
          }
        } else if (state.matchedLocation == '/account-suspended') {
          return '/home';
        }
      } else if (isGuard && state.matchedLocation == '/account-suspended') {
        return '/guard/home';
      }

      if (isGuard && !state.matchedLocation.startsWith('/guard')) {
        return '/guard/home';
      }
      if (!isGuard &&
          state.matchedLocation.startsWith('/guarding') &&
          !hasGuardingClientAccess) {
        return '/menu';
      }

      // Redirect to specific site if landing on /home
      if (isAuthenticated && !isGuard && state.matchedLocation == '/home') {
        final selectedSiteId = ref.read(selectedSiteProvider);
        if (selectedSiteId != null) return '/home/$selectedSiteId';

        final firstSiteId = ref
            .read(siteListProvider)
            .maybeWhen(
              data: (sites) => sites.isNotEmpty ? sites.first.id : null,
              orElse: () => null,
            );
        if (firstSiteId != null) return '/home/$firstSiteId';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/loading',
        builder: (_, _) =>
            const Scaffold(body: Center(child: CircularProgressIndicator())),
      ),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(
        path: '/alarm-alert/:siteId',
        builder: (context, state) => AlarmAlertScreen(
          siteId: state.pathParameters['siteId']!,
          eventId: state.uri.queryParameters['eventId'],
        ),
      ),
      GoRoute(
        path: '/account-suspended',
        builder: (_, _) => const AccountSuspendedScreen(),
      ),
      GoRoute(
        path: '/camera/:siteId/:channelId/:channelName',
        builder: (context, state) => CameraLiveScreen(
          siteId: state.pathParameters['siteId']!,
          channelId: state.pathParameters['channelId']!,
          channelName: state.pathParameters['channelName']!,
        ),
      ),
      GoRoute(path: '/guard/home', builder: (_, _) => const GuardHomeScreen()),
      GoRoute(
        path: '/guard/shift/:assignmentId',
        builder: (context, state) {
          final extra = state.extra;
          final assignment = extra is GuardShiftAssignment
              ? extra
              : GuardShiftAssignment(
                  id: state.pathParameters['assignmentId']!,
                  status: 'assigned',
                  postName: 'Shift',
                  siteName: '',
                );
          return ShiftDetailScreen(assignment: assignment);
        },
      ),
      GoRoute(
        path: '/guard/patrols',
        builder: (context, state) => GuardPatrolScreen(
          assignmentId: state.extra is String ? state.extra as String : null,
        ),
      ),
      GoRoute(
        path: '/guard/dispatch',
        builder: (_, _) => const GuardDispatchScreen(),
      ),
      GoRoute(
        path: '/guard/panic',
        builder: (_, _) => const GuardPanicScreen(),
      ),
      GoRoute(
        path: '/guard/report',
        builder: (_, _) => const GuardReportScreen(),
      ),
      GoRoute(
        path: '/guard/welfare',
        builder: (_, _) => const GuardWelfareScreen(),
      ),
      GoRoute(
        path: '/guard/scan',
        builder: (context, state) => GuardPatrolScanScreen(
          assignmentId: state.extra is String ? state.extra as String : null,
        ),
      ),
      ShellRoute(
        navigatorKey: shellNavigatorKey,
        builder: (context, state, child) => MainScaffold(child: child),
        routes: [
          GoRoute(path: '/messages', builder: (_, _) => const MessagesScreen()),
          GoRoute(
            path: '/home',
            builder: (context, state) => Consumer(
              builder: (context, ref, _) {
                final sitesAsync = ref.watch(siteListProvider);
                return sitesAsync.when(
                  loading: () => const Scaffold(
                    body: Center(child: CircularProgressIndicator()),
                  ),
                  error: (err, _) {
                    return Scaffold(
                      body: Center(
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(
                                Icons.cloud_off_rounded,
                                size: 64,
                                color: Colors.grey,
                              ),
                              const SizedBox(height: 16),
                              const Text(
                                'Unable to connect to Secure Hub',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                err.toString(),
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: Colors.grey,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(height: 24),
                              FilledButton.icon(
                                onPressed: () =>
                                    ref.invalidate(siteListProvider),
                                icon: const Icon(Icons.refresh),
                                label: const Text('Retry Connection'),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                  data: (sites) {
                    if (sites.isEmpty) {
                      return const Scaffold(
                        body: Center(
                          child: Text('No sites associated with this account.'),
                        ),
                      );
                    }
                    // If data exists, the redirect should have kicked in.
                    // If we're here, it might be a race condition, so just show a spinner
                    // while GoRouter processes the next redirect cycle.
                    return const Scaffold(
                      body: Center(child: CircularProgressIndicator()),
                    );
                  },
                );
              },
            ),
            routes: [
              GoRoute(
                path: ':siteId',
                builder: (_, state) => SiteDetailScreen(
                  key: ValueKey(state.pathParameters['siteId']!),
                  siteId: state.pathParameters['siteId']!,
                ),
                routes: [
                  GoRoute(
                    path: 'suspended',
                    builder: (_, state) => SiteSuspendedScreen(
                      siteId: state.pathParameters['siteId']!,
                    ),
                  ),
                  GoRoute(
                    path: 'events',
                    builder: (_, state) => EventListScreen(
                      siteId: state.pathParameters['siteId']!,
                    ),
                  ),
                  GoRoute(
                    path: 'commands',
                    builder: (_, state) => CommandHistoryScreen(
                      siteId: state.pathParameters['siteId']!,
                    ),
                  ),
                ],
              ),
            ],
          ),
          GoRoute(
            path: '/devices',
            builder: (_, _) => const DeviceListScreen(key: ValueKey('devices')),
          ),
          GoRoute(
            path: '/activities',
            builder: (_, _) =>
                const ActivitiesScreen(key: ValueKey('activities')),
          ),
          GoRoute(
            path: '/guarding',
            builder: (_, _) =>
                const ClientGuardingScreen(key: ValueKey('guarding')),
          ),
          GoRoute(
            path: '/menu',
            builder: (_, _) => const MenuScreen(key: ValueKey('menu')),
            routes: [
              GoRoute(
                path: 'profile',
                builder: (_, _) => const ProfileScreen(),
              ),
              GoRoute(
                path: 'notifications',
                builder: (_, _) => const NotificationSettingsScreen(),
              ),
              GoRoute(path: 'help', builder: (_, _) => const HelpScreen()),
            ],
          ),
        ],
      ),
    ],
  );
}
