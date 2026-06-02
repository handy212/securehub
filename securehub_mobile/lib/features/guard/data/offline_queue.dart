import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../../../core/api/guard_endpoints.dart';

final guardOfflineQueueProvider = Provider<GuardOfflineQueue>((ref) {
  return GuardOfflineQueue();
});

class GuardOfflineQueue {
  static const _scanKey = 'guard_offline_scans';
  static const _reportKey = 'guard_offline_reports';

  Future<void> enqueueScan({
    required String patrolRoundId,
    required Map<String, dynamic> payload,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final items = _readList(prefs, _scanKey);
    items.add({
      'patrol_round_id': patrolRoundId,
      'payload': payload,
      'client_scan_id': payload['client_scan_id'] ?? const Uuid().v4(),
    });
    await prefs.setString(_scanKey, jsonEncode(items));
  }

  Future<void> enqueueReport(Map<String, dynamic> payload) async {
    final prefs = await SharedPreferences.getInstance();
    final items = _readList(prefs, _reportKey);
    items.add(payload);
    await prefs.setString(_reportKey, jsonEncode(items));
  }

  Future<int> flush(Dio dio) async {
    final prefs = await SharedPreferences.getInstance();
    var sent = 0;
    final scans = _readList(prefs, _scanKey);
    final remainingScans = <Map<String, dynamic>>[];
    for (final item in scans) {
      try {
        await dio.post(
          GuardEndpoints.patrolScan(item['patrol_round_id'] as String),
          data: item['payload'],
        );
        sent += 1;
      } catch (_) {
        remainingScans.add(item);
      }
    }
    await prefs.setString(_scanKey, jsonEncode(remainingScans));

    final reports = _readList(prefs, _reportKey);
    final remainingReports = <Map<String, dynamic>>[];
    for (final payload in reports) {
      try {
        await dio.post(GuardEndpoints.reports, data: payload);
        sent += 1;
      } catch (_) {
        remainingReports.add(payload);
      }
    }
    await prefs.setString(_reportKey, jsonEncode(remainingReports));
    return sent;
  }

  List<Map<String, dynamic>> _readList(SharedPreferences prefs, String key) {
    final raw = prefs.getString(key);
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    return decoded.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }
}
