import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/guard_endpoints.dart';
import '../models/client_guarding_models.dart';

final clientGuardingApiProvider = Provider<ClientGuardingApi>((ref) {
  return ClientGuardingApi(ref.watch(dioProvider));
});

class ClientGuardingApi {
  const ClientGuardingApi(this._dio);

  final Dio _dio;

  Future<ClientGuardingSnapshot> fetchSnapshot() async {
    try {
      final response = await _dio.get(GuardEndpoints.clientPortal);
      return ClientGuardingSnapshot.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  Future<void> acknowledgeReport(String reportId, {String comment = ''}) async {
    try {
      await _dio.post(
        GuardEndpoints.clientReportAcknowledge(reportId),
        data: comment.isNotEmpty ? {'comment': comment} : null,
      );
    } on DioException catch (e) {
      throwAppException(e);
    }
  }
}
