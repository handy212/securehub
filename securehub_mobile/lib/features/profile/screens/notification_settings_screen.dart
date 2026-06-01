import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_messaging/firebase_messaging.dart' as fcm;
import '../../../core/notifications/notification_settings_notifier.dart';
import '../../../core/notifications/notification_service.dart';
import '../../../core/theme/app_theme.dart';

class NotificationSettingsScreen extends ConsumerWidget {
  const NotificationSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settingsAsync = ref.watch(notificationSettingsProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: Text('Alert Settings',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: settingsAsync.when(
        data: (settings) => ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          children: [
            // OS Level Permission Warning
            FutureBuilder<fcm.NotificationSettings>(
              future: fcm.FirebaseMessaging.instance.getNotificationSettings(),
              builder: (context, snapshot) {
                if (snapshot.hasData &&
                    snapshot.data!.authorizationStatus ==
                        fcm.AuthorizationStatus.denied) {
                  return Container(
                    margin: const EdgeInsets.only(bottom: 24),
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: AppTheme.errorContainer.withValues(alpha: 0.4),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: AppTheme.error.withValues(alpha: 0.1)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.warning_amber_rounded,
                            color: AppTheme.error),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'System permissions denied',
                                style: TextStyle(
                                    color: AppTheme.error,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                'Notifications are blocked in settings.',
                                style: TextStyle(
                                    color: AppTheme.onSurfaceVariant,
                                    fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                        TextButton(
                          onPressed: () => ref
                              .read(notificationServiceProvider)
                              .requestPermission()
                              .then((_) {
                            ref.invalidate(notificationServiceProvider);
                          }),
                          child: Text('ENABLE',
                              style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 12,
                                  color: AppTheme.error)),
                        ),
                      ],
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),

            const _SectionHeader(title: 'Delivery Channels'),
            Material(
              color: AppTheme.surfaceContainerLow,
              borderRadius: BorderRadius.circular(20),
              clipBehavior: Clip.antiAlias,
              child: Column(
                children: [
                  _NotificationToggle(
                    title: 'Push Notifications',
                    subtitle: 'Receive alerts directly on your device',
                    value: settings['push'] ?? true,
                    onChanged: (v) => ref
                        .read(notificationSettingsProvider.notifier)
                        .toggle('push'),
                  ),
                  _NotificationToggle(
                    title: 'Email Reports',
                    subtitle: 'Daily summary of security events',
                    value: settings['email'] ?? true,
                    onChanged: (v) => ref
                        .read(notificationSettingsProvider.notifier)
                        .toggle('email'),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 32),
            const _SectionHeader(title: 'Security Events'),
            Material(
              color: AppTheme.surfaceContainerLow,
              borderRadius: BorderRadius.circular(20),
              clipBehavior: Clip.antiAlias,
              child: Column(
                children: [
                  _NotificationToggle(
                    title: 'Alarm Triggered',
                    subtitle: 'Instant alert when an intruder is detected',
                    value: settings['alarm'] ?? true,
                    onChanged: (v) => ref
                        .read(notificationSettingsProvider.notifier)
                        .toggle('alarm'),
                    isCritical: true,
                  ),
                  _NotificationToggle(
                    title: 'System Armed/Disarmed',
                    subtitle: 'Know when someone changes the status',
                    value: settings['system'] ?? true,
                    onChanged: (v) => ref
                        .read(notificationSettingsProvider.notifier)
                        .toggle('system'),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 32),
            const _SectionHeader(title: 'Maintenance'),
            Material(
              color: AppTheme.surfaceContainerLow,
              borderRadius: BorderRadius.circular(20),
              clipBehavior: Clip.antiAlias,
              child: ListTile(
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                      color: AppTheme.surfaceContainerLowest,
                      borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.notifications_active_outlined,
                      color: AppTheme.primary, size: 20),
                ),
                title: Text('Test notification',
                    style: TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 14)),
                subtitle: Text('Tap to trigger a local test notification',
                    style: TextStyle(
                        fontSize: 12, color: AppTheme.onSurfaceVariant)),
                onTap: () {
                  HapticFeedback.heavyImpact();
                  ref.read(notificationServiceProvider).showTestNotification();
                  
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: const Text('Test notification sent! Check your tray.'),
                      action: SnackBarAction(
                        label: 'OK',
                        onPressed: () {},
                        textColor: AppTheme.secondary,
                      ),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 120),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
            child: Text('Error: $err',
                style: TextStyle(color: AppTheme.error))),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
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
    );
  }
}

class _NotificationToggle extends StatelessWidget {
  const _NotificationToggle({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
    this.isCritical = false,
  });

  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;
  final bool isCritical;

  @override
  Widget build(BuildContext context) {
    return SwitchListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
      title: Text(title,
          style: TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 14,
              color: isCritical && value ? AppTheme.error : AppTheme.primary)),
      subtitle: Text(subtitle,
          style: TextStyle(
              fontSize: 12, color: AppTheme.onSurfaceVariant)),
      value: value,
      activeThumbColor: isCritical ? AppTheme.error : AppTheme.secondary,
      activeTrackColor: (isCritical ? AppTheme.error : AppTheme.secondary)
          .withValues(alpha: 0.35),
      onChanged: (v) {
        HapticFeedback.lightImpact();
        onChanged(v);
      },
    );
  }
}


