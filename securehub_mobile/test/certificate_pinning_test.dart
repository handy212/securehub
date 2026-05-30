import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:securehub_mobile/core/api/certificate_pinning.dart';

void main() {
  test('certificateMatchesPin accepts configured SHA-256 pin', () {
    final der = Uint8List.fromList([1, 2, 3, 4, 5]);
    final pin = base64.encode(sha256.convert(der).bytes);
    final certificate = _FakeCertificate(der);

    expect(certificateMatchesPin(certificate, [pin]), isTrue);
    expect(certificateMatchesPin(certificate, ['other-pin']), isFalse);
  });

  test('loadCertificatePins parses comma-separated dart-define value', () {
    expect(loadCertificatePins(), isEmpty);
  });
}

class _FakeCertificate implements X509Certificate {
  _FakeCertificate(this.der);

  @override
  final Uint8List der;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
