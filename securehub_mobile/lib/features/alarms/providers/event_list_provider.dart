import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_endpoints.dart';
import '../../../core/models/alarm_event.dart';

part 'event_list_provider.g.dart';

@riverpod
class EventListNotifier extends _$EventListNotifier {
  static const _pageSize = 20;

  @override
  Future<List<AlarmEvent>> build(String siteId) async {
    return _fetchPage(1);
  }

  int _currentPage = 1;
  bool _hasMore = true;
  bool _isLoadingMore = false;

  bool get hasMore => _hasMore;
  bool get isLoadingMore => _isLoadingMore;

  Future<List<AlarmEvent>> _fetchPage(int page) async {
    final dio = ref.read(dioProvider);
    try {
      final resp = await dio.get(
        ApiEndpoints.siteEvents(siteId),
        queryParameters: {'page': page, 'page_size': _pageSize},
      );
      final data = Map<String, dynamic>.from(resp.data as Map);
      final results = (data['results'] as List<dynamic>? ?? const [])
          .whereType<Map>()
          .map((item) => _normalizeEventJson(Map<String, dynamic>.from(item)))
          .map((json) {
            try {
              return AlarmEvent.fromJson(json);
            } catch (e) {
              debugPrint('Error parsing AlarmEvent: $e\nJSON: $json');
              rethrow;
            }
          })
          .toList();
      _hasMore = data['next'] != null;
      _currentPage = page;
      return results;
    } on DioException catch (e) {
      throwAppException(e);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> loadMore() async {
    if (!_hasMore || _isLoadingMore) return;
    _isLoadingMore = true;
    final current = state.valueOrNull ?? [];
    
    // Set state to loading while keeping existing data to trigger UI spinner
    state = AsyncLoading<List<AlarmEvent>>().copyWithPrevious(state);

    try {
      final more = await _fetchPage(_currentPage + 1);
      state = AsyncData([...current, ...more]);
    } catch (e, stack) {
      // Keep existing data but surface error if it's the first page failure
      // or if we want to show error at bottom (here we just log and keep current)
      if (current.isEmpty) {
        state = AsyncError(e, stack);
      } else {
        // Option: show a snackbar or just log. Setting state to error
        // will wipe the list in the current UI implementation.
        debugPrint('Error loading more events: $e');
      }
    } finally {
      _isLoadingMore = false;
    }
  }

  Future<void> refresh() async {
    _currentPage = 1;
    _hasMore = true;
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => _fetchPage(1));
  }
}

@riverpod
List<AlarmEvent> filteredEvents(FilteredEventsRef ref, String siteId,
    {String query = '', String filter = 'all'}) {
  final events = ref.watch(eventListNotifierProvider(siteId)).valueOrNull ?? [];

  return events.where((e) {
    final titleMatch =
    e.displayTitle.toLowerCase().contains(query.toLowerCase());
    final subtitleMatch =
    e.displaySubtitle.toLowerCase().contains(query.toLowerCase());
    final performerMatch =
        e.performedBy?.toLowerCase().contains(query.toLowerCase()) ?? false;
    final locationMatch =
    e.fullLocation.toLowerCase().contains(query.toLowerCase());
    final searchMatch =
        query.isEmpty ||
            titleMatch ||
            subtitleMatch ||
            performerMatch ||
            locationMatch;

    final typeMatch = filter == 'all' ||
        (filter == 'alarm' && e.eventCategory == 'alarm') ||
        (filter == 'operation' && e.isOperationEvent) ||
        (filter == 'system' && e.eventCategory != 'alarm' && !e.isOperationEvent);

    return searchMatch && typeMatch;
  }).toList();
}

Map<String, dynamic> _normalizeEventJson(Map<String, dynamic> json) {
  final payloadValue = json['payload'];
  final payload = _compactPayload(
    payloadValue is Map<String, dynamic>
        ? Map<String, dynamic>.from(payloadValue)
        : payloadValue is Map
        ? Map<String, dynamic>.from(payloadValue)
        : <String, dynamic>{},
  );

  final eventName = json['event_name']?.toString().trim();
  if (eventName != null && eventName.isNotEmpty) {
    payload['event_name'] = eventName;
  }

  final normalizedType = json['normalized_event_type']?.toString().trim();
  if (normalizedType != null && normalizedType.isNotEmpty) {
    payload['normalized_event_type'] = normalizedType;
  }

  json['payload'] = payload;
  return json;
}

Map<String, dynamic> _compactPayload(Map<String, dynamic> payload) {
  final compact = <String, dynamic>{};

  void copyIfPresent(String key) {
    try {
      final value = payload[key];
      if (value != null) {
        if (value is Map) {
          compact[key] = Map<String, dynamic>.from(value);
        } else if (value is List) {
          compact[key] = List<dynamic>.from(value);
        } else {
          compact[key] = value;
        }
      }
    } catch (_) {}
  }

  copyIfPresent('event_name');
  copyIfPresent('normalized_event_type');
  copyIfPresent('raw_event_type');
  copyIfPresent('source');
  copyIfPresent('url');
  copyIfPresent('videoUrl');
  copyIfPresent('media_path');

  try {
    final pictures = payload['pictures'];
    if (pictures is List) {
      compact['pictures'] = pictures.take(4).toList();
    }
  } catch (_) {}

  Map<String, dynamic>? compactAlarmData(dynamic raw) {
    if (raw is! Map) return null;
    try {
      final map = Map<String, dynamic>.from(raw);
      final result = <String, dynamic>{};

      void keep(String key) {
        final value = map[key];
        if (value != null) result[key] = value;
      }

      keep('url');
      keep('videoUrl');
      keep('deviceSerial');
      keep('eventType');
      keep('eventDescription');

      final pictureList =
          map['pictureList'] ?? map['picture_list'] ?? map['mediaList'];
      if (pictureList is List) {
        result['pictureList'] = pictureList.take(4).toList();
      }

      return result.isEmpty ? null : result;
    } catch (_) {
      return null;
    }
  }

  final alarmData = compactAlarmData(payload['alarmData']);
  if (alarmData != null) {
    compact['alarmData'] = alarmData;
  }

  final legacyAlarmData = compactAlarmData(payload['alarm_data']);
  if (legacyAlarmData != null) {
    compact['alarm_data'] = legacyAlarmData;
  }

  return compact;
}

// ---------------------------------------------------------------------------
// Alarm picture fetcher (on-demand per event)
// ---------------------------------------------------------------------------

@riverpod
Future<List<AlarmPicture>> alarmPictures(
    Ref ref, String siteId, AlarmEvent event) async {
  final dio = ref.watch(dioProvider);
  final eventId = event.id;

  List<AlarmPicture> payloadPics = [];
  final data = event.payload;
  final alarmData = data['alarmData'] ?? data['alarm_data'] ?? data;

  if (alarmData is Map<String, dynamic>) {
    final list = alarmData['pictureList'] ?? alarmData['picture_list'] ?? alarmData['mediaList'];
    if (list is List) {
      payloadPics = list.map((item) {
        final map = item is Map<String, dynamic> ? item : {'url': item.toString()};
        final urlStr = (map['url'] ?? map['filePath'] ?? map['path'] ?? '').toString();
        final isVideo = urlStr.toLowerCase().contains('.mp4') ||
            urlStr.contains('isDevVideo=1') ||
            urlStr.contains('-2-') ||
            (map['type'] == 'video');
        return AlarmPicture(
          url: urlStr,
          type: isVideo ? 'video' : 'image',
        );
      }).where((p) => p.url.isNotEmpty).toList();
    } else if (alarmData['url'] != null || alarmData['videoUrl'] != null) {
      payloadPics.add(AlarmPicture(
        url: alarmData['url'] ?? alarmData['videoUrl'],
        type: 'video',
      ));
    }
  }
  // Check direct keys if still empty
  if (payloadPics.isEmpty && (data['url'] != null || data['media_path'] != null)) {
    payloadPics.add(AlarmPicture(
      url: data['url'] ?? data['media_path'],
      type: 'video',
    ));
  }

  try {
    final resp = await dio.post(ApiEndpoints.eventPicture(siteId, eventId));
    final apiPics = (resp.data['pictures'] as List)
        .cast<Map<String, dynamic>>()
        .map((json) => AlarmPicture.fromJson(json))
        .toList();

    // Merge API pics and payload pics, prioritizing API data for the same URL
    final allPics = [...apiPics, ...payloadPics];
    final seenUrls = <String>{};
    final uniquePics = <AlarmPicture>[];

    for (final p in allPics) {
      if (seenUrls.add(p.url)) {
        // Auto-detect video type based on URL extension or patterns
        final url = p.url.toLowerCase();
        final isVideoExtension = url.contains('.mp4') ||
            url.contains('.mov') ||
            url.contains('.m4v') ||
            url.contains('.avi');
        final isS3Video = url.contains('s3.eu-west-1.amazonaws.com') ||
            url.contains('amazonaws.com') && url.contains('alarm.eu');

        if (p.type == 'image' && (isVideoExtension || isS3Video)) {
          uniquePics.add(p.copyWith(type: 'video'));
        } else {
          uniquePics.add(p);
        }
      }
    }
    return uniquePics;
  } on DioException catch (e) {
    // If API fails but we have payload pics, return them
    if (payloadPics.isNotEmpty) return payloadPics;
    throwAppException(e);
  }
}
