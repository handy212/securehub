import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:shared_preferences/shared_preferences.dart';

part 'biometric_lock_service.g.dart';

const _kEnabledKey = 'biometric_lock_enabled';
const _kIdleTimeoutSeconds = 5 * 60; // 5 minutes

/// Whether the app is currently showing the lock screen.
@riverpod
class AppLocked extends _$AppLocked {
  @override
  bool build() => false;

  void lock() => state = true;
  void unlock() => state = false;
}

@riverpod
BiometricLockService biometricLockService(Ref ref) =>
    BiometricLockService(ref: ref);

class BiometricLockService {
  BiometricLockService({required Ref ref}) : _ref = ref;

  final Ref _ref;
  final _auth = LocalAuthentication();

  DateTime? _lastActiveAt;

  // -------------------------------------------------------------------------
  // Preference
  // -------------------------------------------------------------------------

  Future<bool> isEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kEnabledKey) ?? false;
  }

  Future<void> setEnabled({required bool enabled}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kEnabledKey, enabled);

    if (enabled) {
      _lastActiveAt = DateTime.now();
      return;
    }

    _lastActiveAt = null;
    _ref.read(appLockedProvider.notifier).unlock();
  }

  Future<bool> isAvailable() async {
    try {
      final canCheck = await _auth.canCheckBiometrics;
      final isDeviceSupported = await _auth.isDeviceSupported();
      final availableBiometrics = await _auth.getAvailableBiometrics();
      return canCheck || isDeviceSupported || availableBiometrics.isNotEmpty;
    } on PlatformException {
      return false;
    }
  }

  // -------------------------------------------------------------------------
  // Lifecycle
  // -------------------------------------------------------------------------

  /// Call when the app moves to background / becomes inactive.
  void onBackground() {
    _lastActiveAt = DateTime.now();
  }

  /// Call when the app resumes from background.
  /// If biometric lock is enabled and idle > 5 min, lock the app.
  Future<void> onResume() async {
    if (!await isEnabled()) return;
    final last = _lastActiveAt;
    if (last == null) return;
    final idleSeconds = DateTime.now().difference(last).inSeconds;
    if (idleSeconds >= _kIdleTimeoutSeconds) {
      _ref.read(appLockedProvider.notifier).lock();
    }
  }

  // -------------------------------------------------------------------------
  // Authentication
  // -------------------------------------------------------------------------

  /// Prompts the biometric / device-credential dialog.
  /// Returns true on success; false if the user cancels or it fails.
  Future<bool> authenticate() async {
    try {
      final success = await _auth.authenticate(
        localizedReason: 'Unlock Secure Hub',
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: false, // allow PIN/pattern fallback
        ),
      );
      if (success) {
        _lastActiveAt = DateTime.now();
        _ref.read(appLockedProvider.notifier).unlock();
      }
      return success;
    } on PlatformException catch (e, stack) {
      if (kDebugMode) {
        debugPrint(
          'BIOMETRIC_AUTH_PLATFORM_ERROR: code=${e.code}, message=${e.message}, details=${e.details}',
        );
        debugPrintStack(stackTrace: stack);
      }
      return false;
    }
  }
}
