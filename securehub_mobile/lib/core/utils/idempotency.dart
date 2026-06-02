import 'package:uuid/uuid.dart';

const _uuid = Uuid();

/// Generate a new idempotency key for use in arm/disarm commands.
String newIdempotencyKey() => _uuid.v4();
