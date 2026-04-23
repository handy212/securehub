import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_endpoints.dart';
import '../../../core/models/site_runtime_inventory.dart';
import '../../../core/auth/auth_notifier.dart';

final siteRuntimeSnapshotProvider =
    StreamProvider.autoDispose.family<SiteRuntimeSnapshot, String>((
  ref,
  siteId,
) async* {
  final authState = ref.watch(authNotifierProvider);
  if (authState is! AuthAuthenticated) {
    return;
  }

  final dio = ref.watch(dioProvider);
  var isDisposed = false;

  ref.onDispose(() {
    isDisposed = true;
  });

  Future<SiteRuntimeSnapshot> fetch() async {
    final resp = await dio.get(ApiEndpoints.sitePoll(siteId));
    return SiteRuntimeSnapshot.fromJson(
      Map<String, dynamic>.from(resp.data as Map),
    );
  }

  try {
    yield await fetch();
  } on DioException catch (e) {
    if (!isDisposed) {
      throwAppException(e);
    }
  }

  while (!isDisposed) {
    await Future.delayed(const Duration(seconds: 10));
    if (isDisposed) break;

    try {
      yield await fetch();
    } on DioException catch (e) {
      if (isDisposed) break;
      throwAppException(e);
    }
  }
});
