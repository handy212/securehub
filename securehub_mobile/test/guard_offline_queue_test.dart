import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:securehub_mobile/features/guard/data/offline_queue.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
  });

  test('enqueueScan stores payload for later flush', () async {
    final queue = GuardOfflineQueue();
    await queue.enqueueScan(
      patrolRoundId: 'round-1',
      payload: {'client_scan_id': 'scan-abc', 'checkpoint_id': 'cp-1'},
    );

    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('guard_offline_scans');
    expect(raw, isNotNull);
    expect(raw, contains('round-1'));
    expect(raw, contains('scan-abc'));
  });

  test('flush sends queued scans and clears successful items', () async {
    final queue = GuardOfflineQueue();
    await queue.enqueueScan(
      patrolRoundId: 'round-1',
      payload: {'client_scan_id': 'scan-1'},
    );

    var requestCount = 0;
    final dio = Dio();
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          requestCount += 1;
          handler.resolve(
            Response(
              requestOptions: options,
              statusCode: 201,
              data: const {},
            ),
          );
        },
      ),
    );

    final sent = await queue.flush(dio);
    expect(sent, 1);
    expect(requestCount, 1);

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('guard_offline_scans'), '[]');
  });
}
