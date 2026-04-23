import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_endpoints.dart';
import '../../../core/api/exceptions.dart';
import '../../../core/auth/auth_notifier.dart';
import '../../../core/models/site.dart';
import '../../../core/models/site_poll.dart';

part 'sites_provider.g.dart';

// ---------------------------------------------------------------------------
// Site list
// ---------------------------------------------------------------------------

@riverpod
Future<List<Site>> siteList(Ref ref) async {
  final authState = ref.watch(authNotifierProvider);
  if (authState is! AuthAuthenticated) return [];

  final dio = ref.watch(dioProvider);
  try {
    final resp = await dio.get(ApiEndpoints.sites);
    final data = resp.data;
    if (data is List) {
      return data.cast<Map<String, dynamic>>().map(Site.fromJson).toList();
    } else if (data is Map<String, dynamic>) {
      return PaginatedSites.fromJson(data).results;
    }
    throw ApiException(
      statusCode: 0,
      message: 'Unexpected response format: ${data.runtimeType}',
    );
  } on DioException catch (e) {
    throwAppException(e);
  }
}

// ---------------------------------------------------------------------------
// Site detail (single site)
// ---------------------------------------------------------------------------

@riverpod
Future<Site> siteDetail(Ref ref, String siteId) async {
  final authState = ref.watch(authNotifierProvider);
  if (authState is! AuthAuthenticated) {
    throw const UnauthorizedException();
  }

  final dio = ref.watch(dioProvider);
  try {
    final resp = await dio.get(ApiEndpoints.siteDetail(siteId));
    return Site.fromJson(resp.data as Map<String, dynamic>);
  } on DioException catch (e) {
    throwAppException(e);
  }
}

// ---------------------------------------------------------------------------
// Force-refresh from hardware — calls SiteStatusView (slow, hits Hik device)
// Returns a SitePoll-shaped object from the status serializer.
// ---------------------------------------------------------------------------

@riverpod
class HardwareRefresh extends _$HardwareRefresh {
  @override
  AsyncValue<void> build(String siteId) => const AsyncData(null);

  Future<void> refresh() async {
    state = const AsyncLoading();
    final dio = ref.read(dioProvider);
    try {
      await dio.get(ApiEndpoints.siteStatus(siteId));
      // After the hardware sync, invalidate both poll and detail to pick up fresh data.
      ref.invalidate(sitePollProvider(siteId));
      ref.invalidate(siteDetailProvider(siteId));
      state = const AsyncData(null);
    } on DioException catch (e) {
      state = AsyncError(e, StackTrace.current);
    }
  }
}

// ---------------------------------------------------------------------------
// Site poll — periodic fast status (DB-only, 10s interval)
// ---------------------------------------------------------------------------

@riverpod
Stream<SitePoll> sitePoll(Ref ref, String siteId) async* {
  final authState = ref.watch(authNotifierProvider);
  if (authState is! AuthAuthenticated) return;

  final dio = ref.watch(dioProvider);
  bool isDisposed = false;

  ref.onDispose(() {
    isDisposed = true;
  });

  Future<SitePoll> fetch() async {
    try {
      final resp = await dio.get(ApiEndpoints.sitePoll(siteId));
      return SitePoll.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  // Emit immediately, then every 10 seconds.
  // The first fetch is allowed to surface an error (e.g. suspension).
  // Subsequent poll failures are logged and skipped — a transient network
  // hiccup must not terminate the stream permanently.
  try {
    yield await fetch();
  } catch (e) {
    if (!isDisposed) rethrow;
    return;
  }

  while (!isDisposed) {
    await Future.delayed(const Duration(seconds: 10));
    if (isDisposed) break;

    try {
      final result = await fetch();
      if (isDisposed) break;
      yield result;
    } catch (e) {
      if (isDisposed) break;
      // Transient error — log and retry on the next tick rather than
      // crashing the stream and leaving the UI stuck on stale data.
      debugPrint('sitePoll[$siteId] fetch error (will retry): $e');
    }
  }
}
@riverpod
Future<String> cameraLiveUrl(CameraLiveUrlRef ref, String siteId, String channelId) async {
  final dio = ref.watch(dioProvider);
  try {
    final resp = await dio.get(ApiEndpoints.cameraLive(siteId, channelId));
    final data = resp.data as Map<String, dynamic>;
    return data['url'] as String;
  } on DioException catch (e) {
    throwAppException(e);
  }
}
