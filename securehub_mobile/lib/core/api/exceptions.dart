/// Thrown for any non-2xx HTTP response from the API.
class ApiException implements Exception {
  const ApiException({required this.statusCode, required this.message});

  final int statusCode;
  final String message;

  @override
  String toString() => message;
}

/// Thrown when a site returns 403 with the subscription suspension message.
/// Carry the [siteId] so the router can navigate to the suspension screen.
class SuspensionException implements Exception {
  const SuspensionException(this.siteId);

  final String siteId;

  @override
  String toString() => 'SuspensionException(siteId: $siteId)';
}

/// Thrown when the account-level permission returns 403 — the user owns at
/// least one site with a suspended/cancelled subscription and is locked out of
/// the entire app until payment is settled.
class AccountSuspendedException implements Exception {
  const AccountSuspendedException();

  @override
  String toString() => 'AccountSuspendedException';
}

/// Thrown when the user is not authenticated and token refresh has failed.
class UnauthorizedException implements Exception {
  const UnauthorizedException();
}

/// Thrown on network connectivity issues (no response received).
class NetworkException implements Exception {
  const NetworkException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Thrown when the app is missing required build-time configuration.
class AppConfigurationException implements Exception {
  const AppConfigurationException(this.message);

  final String message;

  @override
  String toString() => message;
}
