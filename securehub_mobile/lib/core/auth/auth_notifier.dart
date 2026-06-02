import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../models/session_profile.dart';
import '../models/user.dart';
import '../api/api_client.dart';
import '../biometric/biometric_lock_service.dart';
import '../notifications/notification_service.dart';
import 'auth_repository.dart';

part 'auth_notifier.g.dart';

sealed class AuthState {}

class AuthLoading extends AuthState {}

class AuthAuthenticated extends AuthState {
  AuthAuthenticated(this.session);
  final SessionProfile session;

  CustomerProfile get profile => session.customer;
  bool get isGuard => session.isGuard;
}

class AuthUnauthenticated extends AuthState {}

@riverpod
class AuthNotifier extends _$AuthNotifier {
  @override
  AuthState build() {
    restoreSession();
    return AuthLoading();
  }

  Future<void> restoreSession() async {
    try {
      final repo = ref.read(authRepositoryProvider);
      final hasTokens = await repo.hasStoredTokens();
      if (!hasTokens) {
        state = AuthUnauthenticated();
        return;
      }
      final session = await repo.fetchProfile();
      state = AuthAuthenticated(session);
      ref.read(forceLogoutProvider.notifier).reset();
      // Re-register FCM token on session restore (token may have rotated).
      ref.read(notificationServiceProvider).registerToken();
    } catch (_) {
      state = AuthUnauthenticated();
    }
  }

  Future<void> login(String username, String password) async {
    state = AuthLoading();
    try {
      final session = await ref
          .read(authRepositoryProvider)
          .login(username, password);
      state = AuthAuthenticated(session);
      ref.read(forceLogoutProvider.notifier).reset();
      // Register FCM token; non-fatal if it fails.
      ref.read(notificationServiceProvider).registerToken();
    } catch (_) {
      state = AuthUnauthenticated();
      rethrow;
    }
  }

  Future<void> signInWithGoogle() async {
    state = AuthLoading();
    try {
      final session = await ref.read(authRepositoryProvider).signInWithGoogle();
      state = AuthAuthenticated(session);
      ref.read(forceLogoutProvider.notifier).reset();
      // Register FCM token; non-fatal if it fails.
      ref.read(notificationServiceProvider).registerToken();
    } catch (_) {
      state = AuthUnauthenticated();
      rethrow;
    }
  }

  Future<void> logout() async {
    final repo = ref.read(authRepositoryProvider);
    final biometricEnabled = await ref
        .read(biometricLockServiceProvider)
        .isEnabled();

    await ref.read(notificationServiceProvider).deregisterToken();
    await repo.googleSignOut();

    if (!biometricEnabled) {
      await repo.logout();
    }

    ref.read(forceLogoutProvider.notifier).reset();
    state = AuthUnauthenticated();
  }
}
