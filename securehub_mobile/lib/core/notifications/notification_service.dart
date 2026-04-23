import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../features/alarms/providers/event_list_provider.dart';
import '../../features/sites/providers/sites_provider.dart';
import '../../features/sites/providers/site_runtime_provider.dart';
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import 'notification_settings_notifier.dart';

part 'notification_service.g.dart';

bool shouldShowForegroundNotification(
  Map<String, bool> settings, {
  required String? type,
}) {
  if (settings['push'] == false) return false;
  if (type == 'alarm' && settings['alarm'] == false) return false;
  if ((type == 'system' || type == 'status_update') &&
      settings['system'] == false) {
    return false;
  }
  if ((type == 'general' ||
          type == 'billing' ||
          type == 'billing_lockout' ||
          type == 'alert') &&
      settings['messages'] == false) {
    return false;
  }
  return true;
}

@riverpod
class NotificationNav extends _$NotificationNav {
  @override
  String? build() => null;

  void setSiteId(String siteId) => state = siteId;
  void clear() => state = null;
}

@riverpod
class CriticalAlarmNav extends _$CriticalAlarmNav {
  @override
  Map<String, String>? build() => null;

  void trigger(String siteId, {String? eventId}) {
    state = {'site_id': siteId, if (eventId != null) 'event_id': eventId};
  }

  void clear() => state = null;
}

final siteNotificationNavProvider =
    StateProvider<String?>((ref) => null);

@riverpod
class BillingLockoutNav extends _$BillingLockoutNav {
  @override
  bool build() => false;

  void trigger() => state = true;
  void clear() => state = false;
}

@riverpod
class MessagesNav extends _$MessagesNav {
  @override
  bool build() => false;

  void trigger() => state = true;
  void clear() => state = false;
}

@pragma('vm:entry-point')
Future<void> _onBackgroundMessage(RemoteMessage _) async {
  // Background messages are handled when the user taps the notification.
}

@Riverpod(keepAlive: true)
NotificationService notificationService(Ref ref) =>
    NotificationService(ref: ref);

class NotificationService {
  NotificationService({required Ref ref}) : _ref = ref;

  final Ref _ref;
  final _local = FlutterLocalNotificationsPlugin();
  final Map<String, Timer> _refreshDebouncers = {};

  static const _brandColor = Color(0xFFBA1A1A); // AppTheme.error
  static const _smallIcon = '@drawable/ic_stat_securehub';
  static const _largeIcon = '@mipmap/launcher_icon';

  static const _alarmChannelId = 'securehub_alarms';
  static const _alarmChannelName = 'Alarm Alerts';
  static const _alarmChannelDescription = 'Critical security alarm alerts';

  static const _activityChannelId = 'securehub_activity';
  static const _activityChannelName = 'Activity Updates';
  static const _activityChannelDescription =
      'System activity and general updates';
  static const _messageChannelId = 'securehub_messages';
  static const _messageChannelName = 'Provider Messages';
  static const _messageChannelDescription =
      'Provider notices, billing updates, and inbox-style messages';

  static const _alarmGroupKey = 'securehub_alarm_group';
  static const _activityGroupKey = 'securehub_activity_group';
  static const _messageGroupKey = 'securehub_message_group';

  static const _actionOpenEvents = 'open_events';
  static const _actionOpenSite = 'open_site';
  static const _actionOpenMessages = 'open_messages';

  static const _categoryAlarm = 'alarm_category';
  static const _categorySite = 'site_category';
  static const _categoryMessages = 'messages_category';

  bool _ready = false;

  Future<void> initialize() async {
    if (_ready) return;

    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp();
      }
    } catch (_) {
      return;
    }

    _ready = true;
    FirebaseMessaging.onBackgroundMessage(_onBackgroundMessage);

    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(
      alert: false,
      badge: false,
      sound: false,
    );

    const alarmChannel = AndroidNotificationChannel(
      _alarmChannelId,
      _alarmChannelName,
      description: _alarmChannelDescription,
      importance: Importance.max,
      enableVibration: true,
      playSound: true,
    );

    const activityChannel = AndroidNotificationChannel(
      _activityChannelId,
      _activityChannelName,
      description: _activityChannelDescription,
      importance: Importance.high,
      enableVibration: false,
      playSound: true,
    );

    const messageChannel = AndroidNotificationChannel(
      _messageChannelId,
      _messageChannelName,
      description: _messageChannelDescription,
      importance: Importance.defaultImportance,
      enableVibration: false,
      playSound: false,
    );

    final androidPlugin = _local.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await androidPlugin?.createNotificationChannel(alarmChannel);
    await androidPlugin?.createNotificationChannel(activityChannel);
    await androidPlugin?.createNotificationChannel(messageChannel);

    await _local.initialize(
      settings: InitializationSettings(
        android: const AndroidInitializationSettings(_smallIcon),
        iOS: DarwinInitializationSettings(
          notificationCategories: <DarwinNotificationCategory>[
            DarwinNotificationCategory(
              _categoryAlarm,
              actions: <DarwinNotificationAction>[
                DarwinNotificationAction.plain(_actionOpenEvents, 'View Events'),
                DarwinNotificationAction.plain(_actionOpenSite, 'Open Site'),
              ],
            ),
            DarwinNotificationCategory(
              _categorySite,
              actions: <DarwinNotificationAction>[
                DarwinNotificationAction.plain(_actionOpenSite, 'Open Site'),
              ],
            ),
            DarwinNotificationCategory(
              _categoryMessages,
              actions: <DarwinNotificationAction>[
                DarwinNotificationAction.plain(
                  _actionOpenMessages,
                  'Open Messages',
                ),
              ],
            ),
          ],
        ),
      ),
      onDidReceiveNotificationResponse: _handleNotificationResponse,
    );

    final launchDetails = await _local.getNotificationAppLaunchDetails();
    final launchResponse = launchDetails?.notificationResponse;
    if (launchDetails?.didNotificationLaunchApp == true &&
        launchResponse != null) {
      _handleNotificationResponse(launchResponse);
    }

    FirebaseMessaging.onMessage.listen((msg) {
      _log('Foreground message: ${msg.messageId}');
      _showLocal(msg);
    });

    FirebaseMessaging.onMessageOpenedApp.listen((msg) {
      _log('Notification opened app: ${msg.messageId}');
      _handleNotificationTap(msg.data);
    });

    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) {
      _log('Initial message found: ${initial.messageId}');
      _handleNotificationTap(initial.data);
    }

    FirebaseMessaging.instance.onTokenRefresh.listen((_) {
      _log('FCM token refreshed, re-registering');
      registerToken();
    });
  }

  Future<bool> requestPermission() async {
    final settings = await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    return settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
  }

  Future<void> registerToken() async {
    if (!_ready) {
      _log('Service not ready, initializing before token registration');
      await initialize();
      if (!_ready) {
        _log('Cannot register token: notification service unavailable');
        return;
      }
    }

    try {
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null) {
        _log('Failed to get FCM token');
        return;
      }

      final dio = _ref.read(dioProvider);
      final response = await dio.post(
        ApiEndpoints.registerDevice,
        data: {
          'token': token,
          'platform': Platform.isIOS ? 'ios' : 'android',
        },
      );
      _log('Token registration success: ${response.statusCode}');
    } catch (e) {
      _log('Token registration failed: $e');
    }
  }

  Future<void> deregisterToken() async {
    if (!_ready) return;

    try {
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null) return;

      final dio = _ref.read(dioProvider);
      await dio.delete(ApiEndpoints.registerDevice, data: {'token': token});
    } catch (_) {}
  }

  void showTestNotification({String type = 'alarm'}) {
    final payload = <String, String>{
      'type': type,
      'site_id': 'demo-site',
      if (type == 'alarm') 'event_id': 'test-event-123',
    };

    final title = type == 'alarm' ? 'SECURE HUB ALARM' : 'SECURE HUB Test';
    final body = type == 'alarm' 
        ? 'CRITICAL: Motion detected in LIVING ROOM'
        : 'This is a test notification confirming your system is connected.';

    _local.show(
      id: type.hashCode,
      title: title,
      body: body,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _alarmChannelId,
          _alarmChannelName,
          channelDescription: _alarmChannelDescription,
          importance: Importance.max,
          priority: Priority.high,
          playSound: true,
          category: AndroidNotificationCategory.alarm,
          icon: _smallIcon,
          largeIcon: const DrawableResourceAndroidBitmap(_largeIcon),
          color: _brandColor,
          actions: <AndroidNotificationAction>[
            const AndroidNotificationAction(
              _actionOpenEvents,
              'View Events',
              showsUserInterface: true,
            ),
            const AndroidNotificationAction(
              _actionOpenSite,
              'Open Site',
              showsUserInterface: true,
            ),
          ],
          styleInformation: BigTextStyleInformation(
            body,
            contentTitle: title,
            summaryText: 'Security Alert',
          ),
        ),
        iOS: DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
          subtitle: 'Security Alert',
          categoryIdentifier: _categoryAlarm,
          interruptionLevel: InterruptionLevel.timeSensitive,
        ),
      ),
      payload: jsonEncode(payload),
    );
  }

  void _handleNotificationResponse(NotificationResponse response) {
    final payload = response.payload;
    if (payload == null || payload.isEmpty) return;

    try {
      final decoded = jsonDecode(payload);
      if (decoded is! Map<String, dynamic>) return;

      if (response.notificationResponseType ==
              NotificationResponseType.selectedNotificationAction &&
          response.actionId != null) {
        _handleNotificationAction(response.actionId!, decoded);
        return;
      }

      _handleNotificationTap(decoded);
    } catch (e) {
      _log('Failed to handle notification response: $e');
    }
  }

  void _handleNotificationAction(String actionId, Map<String, dynamic> data) {
    switch (actionId) {
      case _actionOpenMessages:
        _ref.read(messagesNavProvider.notifier).trigger();
        return;
      case _actionOpenEvents:
        final siteId = data['site_id'] as String?;
        if (siteId != null && siteId.isNotEmpty) {
          _ref.read(notificationNavProvider.notifier).setSiteId(siteId);
          return;
        }
        break;
      case _actionOpenSite:
        final siteId = data['site_id'] as String?;
        if (siteId != null && siteId.isNotEmpty) {
          _ref.read(siteNotificationNavProvider.notifier).state = siteId;
          return;
        }
        break;
    }

    _handleNotificationTap(data);
  }

  void _handleNotificationTap(Map<String, dynamic> data) {
    _log('Handling notification tap with data: $data');
    final type = data['type'] as String?;

    if (type == 'billing_lockout') {
      _ref.read(billingLockoutNavProvider.notifier).trigger();
      return;
    }

    if (type == 'general' || type == 'billing' || type == 'alert') {
      _ref.read(messagesNavProvider.notifier).trigger();
      return;
    }

    final siteId = data['site_id'] as String?;
    if (siteId == null || siteId.isEmpty) return;

    if (type == 'alarm') {
      _ref.read(criticalAlarmNavProvider.notifier).trigger(
            siteId,
            eventId: data['event_id'] as String?,
          );
      return;
    }

    if (type == 'system' || type == 'status_update') {
      _ref.read(siteNotificationNavProvider.notifier).state = siteId;
    } else {
      _ref.read(notificationNavProvider.notifier).setSiteId(siteId);
    }
  }

  void _showLocal(RemoteMessage message) {
    final notification = message.notification;
    final data = message.data;
    final type = data['type'] as String?;
    final siteId = data['site_id'] as String?;
    final siteName = data['site_name'] as String?;
    final zoneName = data['zone_name'] as String?;
    final eventLabel =
        data['event_title'] as String? ?? data['event_type'] as String?;

    _log(
      'Processing message: type=$type, siteId=$siteId, hasNotification=${notification != null}',
    );

    if (notification == null) {
      if (siteId != null) {
        _triggerSync(siteId, type);
      }
      return;
    }

    final settings = _ref.read(notificationSettingsProvider).value ??
        const {
          'push': true,
          'alarm': true,
          'system': true,
          'messages': true,
        };

    if (!shouldShowForegroundNotification(settings, type: type)) {
      return;
    }

    final profile = _buildProfile(
      type: type,
      siteName: siteName,
      zoneName: zoneName,
      eventLabel: eventLabel,
      notification: notification,
    );

    final payload = jsonEncode({
      'type': type ?? '',
      'site_id': siteId,
    });

    _local.show(
      id: message.hashCode,
      title: profile.title,
      body: profile.body,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          profile.channelId,
          profile.channelName,
          channelDescription: profile.channelDescription,
          importance: profile.importance,
          priority: profile.priority,
          playSound: profile.playSound,
          enableVibration: profile.enableVibration,
          category: _androidCategoryFor(type),
          icon: _smallIcon,
          largeIcon: const DrawableResourceAndroidBitmap(_largeIcon),
          color: profile.color,
          groupKey: profile.groupKey,
          tag: siteId != null ? '$type-$siteId' : type,
          ticker: profile.title,
          subText: siteName,
          channelShowBadge: true,
          visibility: NotificationVisibility.public,
          actions: profile.actions,
          styleInformation: BigTextStyleInformation(
            profile.body,
            contentTitle: profile.title,
            summaryText: profile.summaryText,
          ),
        ),
        iOS: DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: profile.presentSound,
          subtitle: profile.iosSubtitle,
          threadIdentifier: profile.groupKey,
          categoryIdentifier: profile.darwinCategory,
          interruptionLevel: profile.interruptionLevel,
        ),
      ),
      payload: payload,
    );

    if (siteId != null &&
        (type == 'alarm' || type == 'system' || type == 'status_update')) {
      _triggerSync(siteId, type);
    }
  }

  void _triggerSync(String siteId, String? type) {
    _refreshDebouncers[siteId]?.cancel();
    _refreshDebouncers[siteId] = Timer(const Duration(seconds: 1), () {
      _ref.invalidate(sitePollProvider(siteId));
      _ref.invalidate(siteDetailProvider(siteId));
      _ref.invalidate(siteRuntimeSnapshotProvider(siteId));
      if (type == 'alarm' || type == 'system') {
        _ref.invalidate(eventListNotifierProvider(siteId));
      }
      _refreshDebouncers.remove(siteId);
    });
  }

  void _log(String message) {
    debugPrint('[NotificationService] $message');
  }

  AndroidNotificationCategory? _androidCategoryFor(String? type) {
    switch (type) {
      case 'alarm':
        return AndroidNotificationCategory.alarm;
      case 'billing':
      case 'billing_lockout':
        return AndroidNotificationCategory.status;
      case 'general':
      case 'alert':
        return AndroidNotificationCategory.message;
      default:
        return AndroidNotificationCategory.status;
    }
  }

  String _defaultTitle(String? type, String? siteName) {
    switch (type) {
      case 'alarm':
        return siteName == null
            ? 'Alarm Triggered'
            : 'Alarm Triggered at $siteName';
      case 'billing_lockout':
        return 'Account Suspended';
      case 'billing':
        return 'Billing Notice';
      case 'general':
        return 'Secure Hub Update';
      default:
        return siteName == null ? 'Activity Update' : '$siteName Update';
    }
  }

  String _defaultBody(
    String? type,
    String? siteName,
    String? zoneName,
    String? eventLabel,
  ) {
    if (type == 'alarm') {
      final sitePart = siteName ?? 'your site';
      final zonePart = zoneName == null ? '' : ' in $zoneName';
      return 'A security alarm was triggered at $sitePart$zonePart. Open the app to review the latest event details.';
    }

    if (eventLabel != null && eventLabel.isNotEmpty) {
      return siteName == null ? eventLabel : '$eventLabel for $siteName.';
    }

    return siteName == null
        ? 'Open Secure Hub to review the latest update.'
        : 'Open Secure Hub to review the latest update for $siteName.';
  }

  _NotificationProfile _buildProfile({
    required String? type,
    required String? siteName,
    required String? zoneName,
    required String? eventLabel,
    required RemoteNotification notification,
  }) {
    final title = notification.title ?? _defaultTitle(type, siteName);
    final body =
        notification.body ?? _defaultBody(type, siteName, zoneName, eventLabel);

    switch (type) {
      case 'alarm':
        return _NotificationProfile(
          channelId: _alarmChannelId,
          channelName: _alarmChannelName,
          channelDescription: _alarmChannelDescription,
          groupKey: _alarmGroupKey,
          importance: Importance.max,
          priority: Priority.high,
          playSound: true,
          enableVibration: true,
          presentSound: true,
          interruptionLevel: InterruptionLevel.timeSensitive,
          color: _brandColor,
          title: title,
          body: body,
          summaryText: siteName == null
              ? 'Immediate attention required'
              : 'Immediate attention required at $siteName',
          iosSubtitle:
              zoneName == null ? 'Critical alarm' : 'Critical alarm in $zoneName',
          darwinCategory: _categoryAlarm,
          actions: const <AndroidNotificationAction>[
            AndroidNotificationAction(
              _actionOpenEvents,
              'View Events',
              showsUserInterface: true,
            ),
            AndroidNotificationAction(
              _actionOpenSite,
              'Open Site',
              showsUserInterface: true,
            ),
          ],
        );
      case 'system':
      case 'status_update':
        return _NotificationProfile(
          channelId: _activityChannelId,
          channelName: _activityChannelName,
          channelDescription: _activityChannelDescription,
          groupKey: _activityGroupKey,
          importance: Importance.high,
          priority: Priority.defaultPriority,
          playSound: true,
          enableVibration: false,
          presentSound: true,
          interruptionLevel: InterruptionLevel.active,
          color: const Color(0xFF080A10), // AppTheme.primary
          title: title,
          body: body,
          summaryText: siteName == null
              ? 'System status changed'
              : 'System status changed for $siteName',
          iosSubtitle: eventLabel ?? 'System activity',
          darwinCategory: _categorySite,
          actions: const <AndroidNotificationAction>[
            AndroidNotificationAction(
              _actionOpenSite,
              'Open Site',
              showsUserInterface: true,
            ),
          ],
        );
      case 'billing':
      case 'billing_lockout':
        return _NotificationProfile(
          channelId: _messageChannelId,
          channelName: _messageChannelName,
          channelDescription: _messageChannelDescription,
          groupKey: _messageGroupKey,
          importance: Importance.high,
          priority: Priority.defaultPriority,
          playSound: false,
          enableVibration: false,
          presentSound: false,
          interruptionLevel: InterruptionLevel.active,
          color: const Color(0xFFBA1A1A), // AppTheme.error
          title: title,
          body: body,
          summaryText: 'Provider account notice',
          iosSubtitle: 'Billing and account',
          darwinCategory: _categoryMessages,
          actions: const <AndroidNotificationAction>[
            AndroidNotificationAction(
              _actionOpenMessages,
              'Open Messages',
              showsUserInterface: true,
            ),
          ],
        );
      case 'general':
      case 'alert':
      default:
        return _NotificationProfile(
          channelId: _messageChannelId,
          channelName: _messageChannelName,
          channelDescription: _messageChannelDescription,
          groupKey: _messageGroupKey,
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
          playSound: false,
          enableVibration: false,
          presentSound: false,
          interruptionLevel: InterruptionLevel.passive,
          color: const Color(0xFF080A10), // AppTheme.primary
          title: title,
          body: body,
          summaryText: siteName == null
              ? 'Secure Hub inbox message'
              : 'Secure Hub inbox message for $siteName',
          iosSubtitle: 'Provider message',
          darwinCategory: _categoryMessages,
          actions: const <AndroidNotificationAction>[
            AndroidNotificationAction(
              _actionOpenMessages,
              'Open Messages',
              showsUserInterface: true,
            ),
          ],
        );
    }
  }
}

class _NotificationProfile {
  const _NotificationProfile({
    required this.channelId,
    required this.channelName,
    required this.channelDescription,
    required this.groupKey,
    required this.importance,
    required this.priority,
    required this.playSound,
    required this.enableVibration,
    required this.presentSound,
    required this.interruptionLevel,
    required this.color,
    required this.title,
    required this.body,
    required this.summaryText,
    required this.iosSubtitle,
    required this.darwinCategory,
    required this.actions,
  });

  final String channelId;
  final String channelName;
  final String channelDescription;
  final String groupKey;
  final Importance importance;
  final Priority priority;
  final bool playSound;
  final bool enableVibration;
  final bool presentSound;
  final InterruptionLevel interruptionLevel;
  final Color color;
  final String title;
  final String body;
  final String summaryText;
  final String iosSubtitle;
  final String darwinCategory;
  final List<AndroidNotificationAction> actions;
}
