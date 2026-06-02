import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/guard_endpoints.dart';
import '../models/guard_models.dart';
import 'offline_queue.dart';

final guardApiProvider = Provider<GuardApi>((ref) {
  return GuardApi(
    dio: ref.watch(dioProvider),
    offlineQueue: ref.watch(guardOfflineQueueProvider),
  );
});

class GuardApi {
  GuardApi({required Dio dio, required GuardOfflineQueue offlineQueue})
    : _dio = dio,
      _offline = offlineQueue;

  final Dio _dio;
  final GuardOfflineQueue _offline;

  Future<List<GuardShiftAssignment>> fetchShifts() async {
    final resp = await _dio.get(GuardEndpoints.shifts);
    return parseGuardList(resp.data, GuardShiftAssignment.fromJson);
  }

  Future<List<GuardPatrolRound>> fetchPatrolRounds() async {
    final resp = await _dio.get(GuardEndpoints.patrolRounds);
    return parseGuardList(resp.data, GuardPatrolRound.fromJson);
  }

  Future<List<GuardDispatchTask>> fetchDispatchTasks() async {
    final resp = await _dio.get(GuardEndpoints.dispatchTasks);
    return parseGuardList(resp.data, GuardDispatchTask.fromJson);
  }

  Future<List<GuardWelfareCheck>> fetchWelfareChecks() async {
    final resp = await _dio.get(GuardEndpoints.welfareChecks);
    return parseGuardList(resp.data, GuardWelfareCheck.fromJson);
  }

  Future<void> confirmWelfareCheck(String checkId, {String note = ''}) async {
    try {
      await _dio.post(
        GuardEndpoints.welfareConfirm(checkId),
        data: note.isNotEmpty ? {'note': note} : null,
      );
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  Future<void> submitFieldReport(GuardFieldReportDraft draft) async {
    await submitReport(draft.toJson());
  }

  Future<void> acceptShift(String assignmentId) async {
    await _postShiftAction(assignmentId, 'accept');
  }

  Future<void> declineShift(String assignmentId, {String note = ''}) async {
    await _postShiftAction(assignmentId, 'decline', note: note);
  }

  Future<void> clockEvent({
    required String assignmentId,
    required String eventType,
    double? latitude,
    double? longitude,
    double? accuracyM,
    bool withinGeofence = false,
  }) async {
    await _dio.post(
      GuardEndpoints.clock(assignmentId),
      data: {
        'event_type': eventType,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
        if (accuracyM != null) 'accuracy_m': accuracyM,
        'within_geofence': withinGeofence,
      },
    );
  }

  Future<GuardScanResult> scanCheckpoint({
    required String patrolRoundId,
    required String checkpointId,
    String? clientScanId,
    double? latitude,
    double? longitude,
    bool withinGeofence = false,
    DateTime? offlineCreatedAt,
  }) async {
    final payload = {
      'checkpoint': checkpointId,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      'within_geofence': withinGeofence,
      if (clientScanId != null) 'client_scan_id': clientScanId,
      if (offlineCreatedAt != null)
        'offline_created_at': offlineCreatedAt.toUtc().toIso8601String(),
    };
    try {
      final resp = await _dio.post(
        GuardEndpoints.patrolScan(patrolRoundId),
        data: payload,
      );
      return GuardScanResult.fromJson(
        Map<String, dynamic>.from(resp.data as Map),
      );
    } on DioException catch (e) {
      if (_isOfflineError(e)) {
        await _offline.enqueueScan(
          patrolRoundId: patrolRoundId,
          payload: payload,
        );
        return const GuardScanResult(queued: true);
      }
      throwAppException(e);
    }
  }

  Future<void> completePatrol(String patrolRoundId) async {
    await _dio.post(GuardEndpoints.patrolComplete(patrolRoundId));
  }

  Future<void> sendLocationPing({
    required String assignmentId,
    required double latitude,
    required double longitude,
    double? accuracyM,
  }) async {
    await _dio.post(
      GuardEndpoints.location,
      data: {
        'assignment': assignmentId,
        'latitude': latitude,
        'longitude': longitude,
        if (accuracyM != null) 'accuracy_m': accuracyM,
      },
    );
  }

  Future<void> raisePanic({
    String? assignmentId,
    String? siteId,
    double? latitude,
    double? longitude,
    String note = '',
  }) async {
    await _dio.post(
      GuardEndpoints.panic,
      data: {
        if (assignmentId != null) 'assignment': assignmentId,
        if (siteId != null) 'site': siteId,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
        'note': note,
      },
    );
  }

  Future<void> transitionDispatch(
    String taskId,
    String action, {
    String note = '',
  }) async {
    try {
      await _dio.post(
        GuardEndpoints.dispatchAction(taskId, action),
        data: note.isNotEmpty ? {'note': note} : null,
      );
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  Future<void> submitReport(Map<String, dynamic> payload) async {
    try {
      await _dio.post(GuardEndpoints.reports, data: payload);
    } on DioException catch (e) {
      if (_isOfflineError(e)) {
        await _offline.enqueueReport(payload);
        return;
      }
      throwAppException(e);
    }
  }

  Future<int> flushOfflineQueue() => _offline.flush(_dio);

  Future<void> _postShiftAction(
    String assignmentId,
    String action, {
    String note = '',
  }) async {
    try {
      await _dio.post(
        GuardEndpoints.shiftAction(assignmentId, action),
        data: note.isNotEmpty ? {'note': note} : null,
      );
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  bool _isOfflineError(DioException e) {
    return e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.unknown;
  }
}
