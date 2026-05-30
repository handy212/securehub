import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:flutter/foundation.dart';

/// SHA-256 certificate pins (base64) from build-time configuration.
///
/// Generate a pin:
/// ```bash
/// openssl s_client -servername api.example.com -connect api.example.com:443 </dev/null 2>/dev/null \
///   | openssl x509 -outform DER \
///   | openssl dgst -sha256 -binary \
///   | openssl enc -base64
/// ```
List<String> loadCertificatePins() {
  const raw = String.fromEnvironment('API_CERT_SHA256_PINS');
  if (raw.trim().isEmpty) {
    return const [];
  }
  return raw
      .split(',')
      .map((pin) => pin.trim())
      .where((pin) => pin.isNotEmpty)
      .toList(growable: false);
}

bool certificateMatchesPin(X509Certificate certificate, List<String> allowedPins) {
  if (allowedPins.isEmpty) {
    return false;
  }
  final digest = sha256.convert(certificate.der);
  final pin = base64.encode(digest.bytes);
  return allowedPins.contains(pin);
}

/// Pins TLS in release builds when [API_CERT_SHA256_PINS] is configured.
void configureCertificatePinning(Dio dio, {required Uri baseUri}) {
  if (!kReleaseMode) {
    return;
  }

  final pins = loadCertificatePins();
  if (pins.isEmpty) {
    return;
  }

  final adapter = dio.httpClientAdapter;
  if (adapter is! IOHttpClientAdapter) {
    return;
  }

  final expectedHost = baseUri.host.toLowerCase();
  adapter.createHttpClient = () {
    final client = HttpClient(context: SecurityContext(withTrustedRoots: false));
    client.badCertificateCallback = (certificate, host, port) {
      if (host.toLowerCase() != expectedHost) {
        return false;
      }
      return certificateMatchesPin(certificate, pins);
    };
    return client;
  };
}
