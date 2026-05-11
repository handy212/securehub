import 'dart:async';

import 'package:dio/dio.dart';

import '../auth/token_storage.dart';
import 'api_endpoints.dart';
import 'exceptions.dart';

const _suspensionMessage =
    'Access to this site has been suspended due to a billing issue';

const _accountSuspensionMessage =
    'Access to the mobile app has been suspended due to an outstanding balance';

/// Attaches JWT access tokens to every request and handles token lifecycle:
/// - Proactive refresh when the token expires within 5 minutes.
/// - One retry with a fresh token on 401 responses.
/// - Concurrent-refresh lock to prevent race conditions.
/// - 403 + suspension message → throws [SuspensionException].
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required TokenStorage tokenStorage,
    required Dio dio,
    required void Function() onForceLogout,
  })  : _tokens = tokenStorage,
        _dio = dio,
        _onForceLogout = onForceLogout;

  final TokenStorage _tokens;
  final Dio _dio;
  final void Function() _onForceLogout;

  bool _isRefreshing = false;
  final List<Completer<String?>> _refreshQueue = [];

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (_isPublicAuthRequest(options.path)) {
      options.headers.remove('Authorization');
      handler.next(options);
      return;
    }

    final token = await _getValidAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final response = err.response;
    if (response == null) {
      handler.next(err);
      return;
    }

    // 403: check for site-level or account-level suspension
    if (response.statusCode == 403) {
      final detail = _extractDetail(response.data);
      if (detail.contains(_accountSuspensionMessage)) {
        handler.reject(
          DioException(
            requestOptions: err.requestOptions,
            error: const AccountSuspendedException(),
          ),
        );
        return;
      }
      if (detail.contains(_suspensionMessage)) {
        final siteId = _extractSiteId(err.requestOptions.path);
        handler.reject(
          DioException(
            requestOptions: err.requestOptions,
            error: SuspensionException(siteId ?? ''),
          ),
        );
        return;
      }
      handler.next(err);
      return;
    }

    // 401: attempt one token refresh then retry
    if (response.statusCode == 401 &&
        !_isPublicAuthRequest(err.requestOptions.path) &&
        !err.requestOptions.path.contains(ApiEndpoints.refresh)) {
      try {
        final newToken = await _refreshAccessToken();
        if (newToken == null) {
          _onForceLogout();
          handler.reject(
            DioException(
              requestOptions: err.requestOptions,
              error: const UnauthorizedException(),
            ),
          );
          return;
        }
        // Retry with the new token
        final retryOptions = err.requestOptions;
        retryOptions.headers['Authorization'] = 'Bearer $newToken';
        final retryResponse = await _dio.fetch(retryOptions);
        handler.resolve(retryResponse);
        return;
      } catch (_) {
        _onForceLogout();
        handler.reject(
          DioException(
            requestOptions: err.requestOptions,
            error: const UnauthorizedException(),
          ),
        );
        return;
      }
    }

    handler.next(err);
  }

  // ---------------------------------------------------------------------------

  Future<String?> _getValidAccessToken() async {
    final token = await _tokens.getAccessToken();
    if (token == null) return null;

    final expiry = TokenStorage.expiryOf(token);
    if (expiry == null) return token;

    final needsRefresh =
        expiry.difference(DateTime.now().toUtc()) < const Duration(minutes: 5);
    if (!needsRefresh) return token;

    return _refreshAccessToken();
  }

  Future<String?> _refreshAccessToken() async {
    // If a refresh is already in progress, queue behind it.
    if (_isRefreshing) {
      final completer = Completer<String?>();
      _refreshQueue.add(completer);
      return completer.future;
    }

    _isRefreshing = true;
    try {
      final refreshToken = await _tokens.getRefreshToken();
      if (refreshToken == null) return null;

      // Use a fresh Dio without interceptors to avoid recursion.
      final plain = Dio(_dio.options);
      final resp = await plain.post(
        ApiEndpoints.refresh,
        data: {'refresh': refreshToken},
      );

      final newAccess = resp.data['access'] as String?;
      final newRefresh = resp.data['refresh'] as String?;
      if (newAccess == null) return null;

      if (newRefresh != null) {
        await _tokens.saveTokens(
            accessToken: newAccess, refreshToken: newRefresh);
      } else {
        await _tokens.saveAccessToken(newAccess);
      }

      for (final c in _refreshQueue) {
        c.complete(newAccess);
      }
      _refreshQueue.clear();
      return newAccess;
    } catch (_) {
      for (final c in _refreshQueue) {
        c.complete(null);
      }
      _refreshQueue.clear();
      return null;
    } finally {
      _isRefreshing = false;
    }
  }

  String _extractDetail(dynamic data) {
    if (data is Map) return (data['detail'] ?? '').toString();
    return data?.toString() ?? '';
  }

  String? _extractSiteId(String path) {
    final match = RegExp(r'/sites/([^/]+)/').firstMatch(path);
    return match?.group(1);
  }

  bool _isPublicAuthRequest(String path) {
    return path.contains(ApiEndpoints.login) ||
        path.contains(ApiEndpoints.googleLogin) ||
        path.contains(ApiEndpoints.passwordReset) ||
        path.contains(ApiEndpoints.refresh) ||
        path.contains(ApiEndpoints.logout);
  }
}
