import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_endpoints.dart';
import '../../../core/models/arm_disarm_command.dart';

part 'command_list_provider.g.dart';

@riverpod
Future<List<ArmDisarmCommand>> commandList(Ref ref, String siteId) async {
  final dio = ref.watch(dioProvider);
  try {
    final resp = await dio.get(ApiEndpoints.siteCommands(siteId));
    final paginated =
        PaginatedCommands.fromJson(resp.data as Map<String, dynamic>);
    return paginated.results;
  } on DioException catch (e) {
    throwAppException(e);
  }
}
