import 'package:flutter_test/flutter_test.dart';
import 'package:securehub_mobile/core/notifications/notification_service.dart';

void main() {
  test('Push disabled suppresses all foreground notifications', () {
    final settings = {
      'push': false,
      'alarm': true,
      'system': true,
      'messages': true,
    };

    expect(shouldShowForegroundNotification(settings, type: 'alarm'), isFalse);
    expect(shouldShowForegroundNotification(settings, type: 'system'), isFalse);
    expect(shouldShowForegroundNotification(settings, type: 'alert'), isFalse);
  });

  test('Alarm notifications respect alarm preference only', () {
    const baseSettings = {
      'push': true,
      'alarm': true,
      'system': false,
      'messages': true,
    };

    expect(
      shouldShowForegroundNotification(baseSettings, type: 'alarm'),
      isTrue,
    );
    expect(
      shouldShowForegroundNotification(
        {...baseSettings, 'alarm': false},
        type: 'alarm',
      ),
      isFalse,
    );
  });

  test('System and status update notifications respect system preference', () {
    const settings = {
      'push': true,
      'alarm': true,
      'system': false,
      'messages': true,
    };

    expect(
      shouldShowForegroundNotification(settings, type: 'system'),
      isFalse,
    );
    expect(
      shouldShowForegroundNotification(settings, type: 'status_update'),
      isFalse,
    );
    expect(
      shouldShowForegroundNotification(
        {...settings, 'system': true},
        type: 'status_update',
      ),
      isTrue,
    );
  });

  test('Message-style notifications follow messages preference', () {
    const settings = {
      'push': true,
      'alarm': true,
      'system': false,
      'messages': true,
    };

    for (final type in ['general', 'billing', 'billing_lockout', 'alert']) {
      expect(
        shouldShowForegroundNotification(settings, type: type),
        isTrue,
        reason: '$type should show when messages are enabled',
      );
      expect(
        shouldShowForegroundNotification(
          {...settings, 'messages': false},
          type: type,
        ),
        isFalse,
        reason: '$type should be suppressed when messages are disabled',
      );
    }
  });

  test('Alert notifications follow messages preference instead of system', () {
    const settings = {
      'push': true,
      'alarm': true,
      'system': false,
      'messages': true,
    };

    expect(
      shouldShowForegroundNotification(settings, type: 'alert'),
      isTrue,
    );
    expect(
      shouldShowForegroundNotification(
        {...settings, 'messages': false},
        type: 'alert',
      ),
      isFalse,
    );
  });

  test('Unknown notification types fall back to push-only gating', () {
    const settings = {
      'push': true,
      'alarm': false,
      'system': false,
      'messages': false,
    };

    expect(
      shouldShowForegroundNotification(settings, type: 'custom_type'),
      isTrue,
    );
    expect(
      shouldShowForegroundNotification(
        {...settings, 'push': false},
        type: 'custom_type',
      ),
      isFalse,
    );
  });
}
