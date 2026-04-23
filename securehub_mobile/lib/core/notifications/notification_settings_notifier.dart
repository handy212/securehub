import 'dart:async';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'notification_settings_notifier.g.dart';

@riverpod
class NotificationSettings extends _$NotificationSettings {
  final _storage = const FlutterSecureStorage();
  
  @override
  FutureOr<Map<String, bool>> build() async {
    final push = await _storage.read(key: 'notif_push') ?? 'true';
    final email = await _storage.read(key: 'notif_email') ?? 'true';
    final alarm = await _storage.read(key: 'notif_alarm') ?? 'true';
    final system = await _storage.read(key: 'notif_system') ?? 'true';

    // Provider/inbox-style notices remain enabled because there is no user-facing
    // control for them in the app anymore.
    await _storage.delete(key: 'notif_sms');
    await _storage.write(key: 'notif_messages', value: 'true');

    return {
      'push': push == 'true',
      'email': email == 'true',
      'alarm': alarm == 'true',
      'system': system == 'true',
      'messages': true,
    };
  }

  Future<void> toggle(String key) async {
    final current = state.value ?? {};
    final newVal = !(current[key] ?? false);
    
    final updated = Map<String, bool>.from(current);
    updated[key] = newVal;
    
    state = AsyncData(updated);
    await _storage.write(key: 'notif_$key', value: newVal.toString());
  }
}
