# securehub_mobile

SecureHub customer and guard mobile client (Flutter).

## Configuration

Release builds require the API base URL:

```bash
flutter run --dart-define=API_BASE_URL=https://api.example.com
```

Optional TLS certificate pinning (release builds only, when pins are set):

```bash
flutter build apk \
  --dart-define=API_BASE_URL=https://api.example.com \
  --dart-define=API_CERT_SHA256_PINS='<pin1>,<pin2>'
```

Generate a SHA-256 pin from the server certificate:

```bash
openssl s_client -servername api.example.com -connect api.example.com:443 </dev/null 2>/dev/null \
  | openssl x509 -outform DER \
  | openssl dgst -sha256 -binary \
  | openssl enc -base64
```

Use multiple comma-separated pins when rotating certificates.

## Tests

```bash
flutter test
```
