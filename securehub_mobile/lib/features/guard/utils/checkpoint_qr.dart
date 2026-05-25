import 'dart:convert';

import '../models/guard_models.dart';

/// Parsed checkpoint reference from a printed QR code or manual entry.
class CheckpointQrReference {
  const CheckpointQrReference({
    this.checkpointId,
    this.checkpointCode,
  });

  final String? checkpointId;
  final String? checkpointCode;

  bool get isValid => (checkpointId?.isNotEmpty ?? false) || (checkpointCode?.isNotEmpty ?? false);
}

final _uuidPattern = RegExp(
  r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
  caseSensitive: false,
);

CheckpointQrReference parseCheckpointQr(String raw) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) {
    return const CheckpointQrReference();
  }

  if (trimmed.startsWith('{')) {
    try {
      final map = jsonDecode(trimmed) as Map<String, dynamic>;
      if (map['type'] == 'guard_checkpoint') {
        return CheckpointQrReference(
          checkpointId: map['checkpoint_id']?.toString(),
          checkpointCode: map['code']?.toString(),
        );
      }
    } catch (_) {
      // Fall through to other parsers.
    }
  }

  if (_uuidPattern.hasMatch(trimmed)) {
    return CheckpointQrReference(checkpointId: trimmed);
  }

  return CheckpointQrReference(checkpointCode: trimmed);
}

/// Match a scanned QR reference to a patrol round checkpoint.
({GuardPatrolRound round, GuardPatrolCheckpoint checkpoint})? matchCheckpointInRounds(
  List<GuardPatrolRound> rounds,
  CheckpointQrReference reference,
) {
  for (final round in rounds) {
    for (final checkpoint in round.route.checkpoints) {
      if (reference.checkpointId != null && checkpoint.id == reference.checkpointId) {
        return (round: round, checkpoint: checkpoint);
      }
      if (reference.checkpointCode != null &&
          reference.checkpointCode!.isNotEmpty &&
          checkpoint.code.toLowerCase() == reference.checkpointCode!.toLowerCase()) {
        return (round: round, checkpoint: checkpoint);
      }
    }
  }
  return null;
}
