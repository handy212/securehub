import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../auth/token_storage.dart';
import 'auth_interceptor.dart';
import 'exceptions.dart';

part 'api_client.g.dart';

// ---------------------------------------------------------------------------
// Base URL
// Set via: flutter run --dart-define=API_BASE_URL=https://api.example.com
// ---------------------------------------------------------------------------
String _getBaseUrl() {
  const envUrl = String.fromEnvironment('API_BASE_URL');
  if (envUrl.isNotEmpty) return envUrl;

  // In release builds with no URL configured, let API callers surface a clear
  // in-app error instead of crashing during provider construction.
  if (kReleaseMode) {
    return '';
  }

  // Local development fallbacks.
  if (kIsWeb) return 'http://localhost:8000';
  return defaultTargetPlatform == TargetPlatform.android
      ? 'http://10.0.2.2:8000'
      : 'http://localhost:8000';
}

final _baseUrl = _getBaseUrl();

const String googleServerClientId = String.fromEnvironment(
  'GOOGLE_SERVER_CLIENT_ID',
);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

@riverpod
Dio dio(Ref ref) {
  if (_baseUrl.isEmpty) {
    throw const AppConfigurationException(
      'Secure Hub is missing its production API URL. '
      'Build with --dart-define=API_BASE_URL=<url>.',
    );
  }

  final tokenStorage = ref.watch(tokenStorageProvider);

  final dioInstance = Dio(
    BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ),
  );

  dioInstance.interceptors.add(
    AuthInterceptor(
      tokenStorage: tokenStorage,
      dio: dioInstance,
      onForceLogout: () => ref.read(forceLogoutProvider.notifier).trigger(),
    ),
  );

  return dioInstance;
}

@riverpod
TokenStorage tokenStorage(Ref ref) => TokenStorage();

@riverpod
Future<String?> accessToken(Ref ref) {
  return ref.watch(tokenStorageProvider).getAccessToken();
}

/// Transforms local URLs (localhost/127.0.0.1) to 10.0.2.2 on Android emulators
/// and ensures relative paths are prepended with the base URL.
String transformUrl(String url) {
  if (url.isEmpty) return '';

  String transformed = url;

  // Prepend base URL if it's a relative path
  if (!transformed.startsWith('http')) {
    transformed =
        _baseUrl + (transformed.startsWith('/') ? '' : '/') + transformed;
  }

  if (defaultTargetPlatform != TargetPlatform.android || !kDebugMode) {
    return transformed;
  }

  // Only transform if the URL contains localhost or 127.0.0.1
  // to avoid breaking absolute external URLs (S3, etc.)
  if (transformed.contains('localhost') || transformed.contains('127.0.0.1')) {
    transformed = transformed
        .replaceAll('localhost', '10.0.2.2')
        .replaceAll('127.0.0.1', '10.0.2.2');
  }

  return transformed;
}

/// Returns true when [url] is a relative URL or points back to this app's API.
/// External signed media URLs should not receive our bearer token headers.
bool shouldAttachApiAuthHeader(String url) {
  if (url.isEmpty) return false;
  if (!url.startsWith('http')) return true;

  final mediaUri = Uri.tryParse(transformUrl(url));
  final apiUri = Uri.tryParse(transformUrl(_baseUrl));
  if (mediaUri == null || apiUri == null) return false;

  return mediaUri.scheme == apiUri.scheme &&
      mediaUri.host == apiUri.host &&
      mediaUri.port == apiUri.port;
}

// ---------------------------------------------------------------------------
// Force-logout notifier — watched by GoRouter to redirect to /login
// ---------------------------------------------------------------------------

@riverpod
class ForceLogout extends _$ForceLogout {
  @override
  bool build() => false;

  void trigger() => state = true;
  void reset() => state = false;
}

// ---------------------------------------------------------------------------
// Helper: convert DioException to typed app exceptions
// ---------------------------------------------------------------------------

Never throwAppException(DioException e) {
  if (e.error is AccountSuspendedException) throw e.error!;
  if (e.error is SuspensionException) throw e.error!;
  if (e.error is UnauthorizedException) throw e.error!;

  final statusCode = e.response?.statusCode ?? 0;
  final data = e.response?.data;
  String message = 'Unexpected error occurred.';

  if (data is Map) {
    if (data['command'] != null) {
      message = data['command'].toString();
    } else if (data['detail'] != null) {
      message = data['detail'].toString();
    } else if (data['message'] != null) {
      message = data['message'].toString();
    } else if (data.isNotEmpty) {
      // If none of the specific fields are found, join values (DRF default style)
      message = data.values.map((v) => v.toString()).join(' ');
    }
  } else if (data is String && data.isNotEmpty) {
    message = data;
  } else {
    message = e.message ?? 'Unknown error';
  }

  if (message.contains('LAP020011')) {
    message = 'Panel communication error. Please try again in a moment.';
  } else if (message.contains('1073774671')) {
    message = 'Unable to arm. Please ensure all doors and windows are closed.';
  } else if (message.contains('Hik-Partner API error')) {
    // Extract the most relevant part if possible, otherwise keep it simple
    final parts = message.split(':');
    if (parts.length > 1) {
      message = parts.last.trim();
    }
  }

  if (e.type == DioExceptionType.connectionError ||
      e.type == DioExceptionType.connectionTimeout) {
    throw NetworkException(message);
  }

  throw ApiException(statusCode: statusCode, message: message);
}
