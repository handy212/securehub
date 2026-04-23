import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/auth/auth_repository.dart';
import '../../../core/api/exceptions.dart';
import '../../../core/biometric/biometric_lock_service.dart';

part 'login_provider.g.dart';

sealed class LoginState {}

class LoginIdle extends LoginState {}

class LoginSubmitting extends LoginState {}

class LoginError extends LoginState {
  LoginError(this.message);
  final String message;
}

@riverpod
class LoginNotifier extends _$LoginNotifier {
  @override
  LoginState build() => LoginIdle();

  Future<void> submit(String username, String password) async {
    if (username.isEmpty || password.isEmpty) {
      state = LoginError('Please enter your username and password.');
      return;
    }
    state = LoginSubmitting();
    try {
      await ref.read(authNotifierProvider.notifier).login(username, password);
      state = LoginIdle();
    } on UnauthorizedException {
      state = LoginError('Invalid username or password.');
    } on ApiException catch (e) {
      if (e.statusCode == 401) {
        state = LoginError('Invalid username or password.');
      } else {
        state = LoginError('Server error (${e.statusCode}). Please try again.');
      }
    } on NetworkException {
      state = LoginError('No connection. Please check your network.');
    } catch (e) {
      debugPrint('LOGIN_NOTIFIER_ERROR: $e');
      state = LoginError('Something went wrong. Please try again.');
    }
  }

  Future<void> signInWithGoogle() async {
    state = LoginSubmitting();
    try {
      await ref.read(authNotifierProvider.notifier).signInWithGoogle();
      state = LoginIdle();
    } catch (e) {
      if (e.toString().toLowerCase().contains('cancelled')) {
        state = LoginIdle(); // Silent fallback on user cancellation
      } else {
        debugPrint('GOOGLE_LOGIN_NOTIFIER_ERROR: $e');
        state = LoginError('Google login failed. Please try again.');
      }
    }
  }

  Future<void> signInWithBiometrics() async {
    state = LoginSubmitting();
    try {
      final lockSvc = ref.read(biometricLockServiceProvider);
      final success = await lockSvc.authenticate();
      if (!success) {
        state = LoginError('Biometric authentication failed or was cancelled.');
        return;
      }

      final repo = ref.read(authRepositoryProvider);
      if (!await repo.hasStoredTokens()) {
        state = LoginError(
          'No stored session found. Please log in with a password first.',
        );
        return;
      }

      await ref.read(authNotifierProvider.notifier).restoreSession();
      // Only set idle if auth state is still unauthenticated (restoreSession didn't throw but failed)
      if (ref.read(authNotifierProvider) is AuthUnauthenticated) {
        state = LoginError('Session expired. Please log in with a password.');
      } else {
        state = LoginIdle();
      }
    } catch (e) {
      debugPrint('BIOMETRIC_LOGIN_ERROR: $e');
      state = LoginError('Something went wrong during biometric login.');
    }
  }

  void clearError() {
    if (state is LoginError) state = LoginIdle();
  }
}
