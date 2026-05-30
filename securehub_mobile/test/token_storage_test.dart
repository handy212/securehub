import 'package:flutter_test/flutter_test.dart';
import 'package:securehub_mobile/core/auth/token_storage.dart';

void main() {
  group('TokenStorage.expiryOf', () {
    test('returns null for malformed token', () {
      expect(TokenStorage.expiryOf('not-a-jwt'), isNull);
      expect(TokenStorage.expiryOf('a.b'), isNull);
    });

    test('parses exp claim from valid JWT payload', () {
      // Header.payload.signature — payload {"exp": 1893456000} (2030-01-01 UTC)
      const token =
          'eyJhbGciOiJIUzI1NiJ9.'
          'eyJleHAiOjE4OTM0NTYwMDB9.'
          'signature';
      final expiry = TokenStorage.expiryOf(token);
      expect(expiry, isNotNull);
      expect(expiry!.year, 2030);
      expect(expiry.month, 1);
      expect(expiry.day, 1);
    });
  });
}
