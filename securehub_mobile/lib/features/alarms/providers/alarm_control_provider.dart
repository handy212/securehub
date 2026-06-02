import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_endpoints.dart';
import '../../../core/api/exceptions.dart';
import '../../../core/models/arm_disarm_command.dart';
import '../../../core/utils/idempotency.dart';

part 'alarm_control_provider.g.dart';

sealed class CommandState {}

class CommandIdle extends CommandState {}

class CommandSending extends CommandState {}

class CommandSuccess extends CommandState {
  CommandSuccess(this.command);
  final ArmDisarmCommand command;
}

class CommandFailed extends CommandState {
  CommandFailed(this.message);
  final String message;
}

@riverpod
class AlarmControlNotifier extends _$AlarmControlNotifier {
  @override
  CommandState build() => CommandIdle();

  Future<void> sendCommand({
    required String siteId,
    required String subsystemId,
    required String action,
    String? operatorUsername,
    String? operatorPassword,
  }) async {
    await sendBulkCommand(
      siteId: siteId,
      subsystemIds: [subsystemId],
      action: action,
      operatorUsername: operatorUsername,
      operatorPassword: operatorPassword,
    );
  }

  Future<void> sendBulkCommand({
    required String siteId,
    required List<String> subsystemIds,
    required String action,
    String? operatorUsername,
    String? operatorPassword,
  }) async {
    if (subsystemIds.isEmpty) return;

    state = CommandSending();
    HapticFeedback.mediumImpact();
    final dio = ref.read(dioProvider);

    try {
      ArmDisarmCommand? lastCmd;

      for (final subId in subsystemIds) {
        final key = newIdempotencyKey();
        final body = <String, dynamic>{'idempotency_key': key};
        if (operatorUsername != null) {
          body['operator_username'] = operatorUsername;
        }
        if (operatorPassword != null) {
          body['operator_password'] = operatorPassword;
        }

        final resp = await dio.post(
          ApiEndpoints.subsystemCommand(siteId, subId, action),
          data: body,
          options: Options(headers: {'X-Idempotency-Key': key}),
        );
        // The view wraps success responses: {"success": true, "data": {...}}
        // Idempotency replay (HTTP 200) returns the flat object directly.
        final raw = resp.data as Map<String, dynamic>;
        final cmdJson = (raw['data'] as Map<String, dynamic>?) ?? raw;
        lastCmd = ArmDisarmCommand.fromJson(cmdJson);
      }

      if (lastCmd != null) {
        state = CommandSuccess(lastCmd);
      }
    } on SuspensionException {
      rethrow;
    } on DioException catch (e) {
      try {
        throwAppException(e);
      } on ApiException catch (error) {
        state = CommandFailed(error.message);
      } catch (ex) {
        state = CommandFailed(ex.toString());
      }
    } catch (e) {
      state = CommandFailed(e.toString());
    }
  }

  void reset() => state = CommandIdle();
}
