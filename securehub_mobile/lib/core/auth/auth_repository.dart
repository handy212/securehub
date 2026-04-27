import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import '../models/user.dart';
import 'token_storage.dart';

part 'auth_repository.g.dart';

@riverpod
AuthRepository authRepository(Ref ref) => AuthRepository(
  dio: ref.watch(dioProvider),
  tokenStorage: ref.watch(tokenStorageProvider),
);

class AuthRepository {
  AuthRepository({required Dio dio, required TokenStorage tokenStorage})
    : _dio = dio,
      _tokens = tokenStorage;

  final Dio _dio;
  final TokenStorage _tokens;

  /// Log in with [username] and [password].
  /// Stores tokens on success and returns the [CustomerProfile].
  Future<CustomerProfile> login(String username, String password) async {
    try {
      final resp = await _dio.post(
        ApiEndpoints.login,
        data: {'username': username, 'password': password},
      );
      final data = resp.data;
      if (data is! Map) {
        if (kDebugMode) {
          debugPrint(
            'LOGIN DATA TYPE ERROR: expected Map, got ${data.runtimeType}',
          );
        }
        throw Exception('Server returned an invalid login response format.');
      }

      final access = data['access'] as String?;
      final refresh = data['refresh'] as String?;

      if (access == null || refresh == null) {
        if (kDebugMode) {
          debugPrint('LOGIN MISSING TOKENS');
        }
        throw Exception('Login successful but no tokens were provided.');
      }

      await _tokens.saveTokens(accessToken: access, refreshToken: refresh);

      final profileResp = await _dio.get(ApiEndpoints.profile);
      final profileData = profileResp.data;
      if (profileData is! Map || profileData.isEmpty) {
        if (kDebugMode) {
          debugPrint('PROFILE INVALID: ${profileData.runtimeType}');
        }
        throw Exception('Server returned an invalid profile response.');
      }

      return CustomerProfile.fromJson(Map<String, dynamic>.from(profileData));
    } on DioException catch (e) {
      throwAppException(e);
    } catch (e, stack) {
      if (kDebugMode) {
        debugPrint('LOGIN UNEXPECTED ERROR: $e');
        debugPrint('STACK: $stack');
      }
      rethrow;
    }
  }

  Future<CustomerProfile> signInWithGoogle() async {
    try {
      final googleSignIn = GoogleSignIn(
        serverClientId: googleServerClientId.isEmpty
            ? null
            : googleServerClientId,
      );
      final googleUser = await googleSignIn.signIn();
      if (googleUser == null) {
        throw Exception('Google Sign-In was cancelled.');
      }

      final googleAuth = await googleUser.authentication;
      final idToken = googleAuth.idToken;

      if (idToken == null) {
        throw Exception('Could not retrieve Google ID Token.');
      }

      final resp = await _dio.post(
        ApiEndpoints.googleLogin,
        data: {'id_token': idToken},
      );

      final data = resp.data;
      final access = data['access'] as String?;
      final refresh = data['refresh'] as String?;

      if (access == null || refresh == null) {
        throw Exception('Server returned no tokens for Google Login.');
      }

      await _tokens.saveTokens(accessToken: access, refreshToken: refresh);

      final profileResp = await _dio.get(ApiEndpoints.profile);
      return CustomerProfile.fromJson(profileResp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throwAppException(e);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('GOOGLE LOGIN ERROR: $e');
      }
      rethrow;
    }
  }

  Future<CustomerProfile> fetchProfile() async {
    try {
      final resp = await _dio.get(ApiEndpoints.profile);
      return CustomerProfile.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  Future<void> logout() async {
    final refreshToken = await _tokens.getRefreshToken();

    try {
      if (refreshToken != null && refreshToken.isNotEmpty) {
        await _dio.post(ApiEndpoints.logout, data: {'refresh': refreshToken});
      }
    } on DioException {
      // Best-effort remote logout. Local sign-out still needs to complete.
    } finally {
      await _tokens.clearTokens();
    }
  }

  Future<void> googleSignOut() async {
    try {
      await GoogleSignIn().signOut();
    } catch (_) {
      // Ignore failures on background sign-out
    }
  }

  Future<bool> hasStoredTokens() async {
    final token = await _tokens.getAccessToken();
    return token != null;
  }
}
