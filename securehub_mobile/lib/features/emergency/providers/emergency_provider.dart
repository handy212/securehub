import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_endpoints.dart';
import '../../../core/api/exceptions.dart';
import '../models/emergency_models.dart';

final emergencyRepositoryProvider = Provider<EmergencyRepository>((ref) {
  return EmergencyRepository(dio: ref.watch(dioProvider));
});

final emergencyLocationServiceProvider = Provider<EmergencyLocationService>((
  _,
) {
  return EmergencyLocationService();
});

final emergencyStatusProvider = FutureProvider.family<EmergencyStatus, String?>(
  (ref, siteId) async {
    return ref.watch(emergencyRepositoryProvider).status(siteId: siteId);
  },
);

final emergencyControllerProvider =
    StateNotifierProvider<EmergencyController, EmergencyState>((ref) {
      return EmergencyController(
        repository: ref.watch(emergencyRepositoryProvider),
        locationService: ref.watch(emergencyLocationServiceProvider),
      );
    });

class EmergencyRepository {
  EmergencyRepository({required Dio dio}) : _dio = dio;

  final Dio _dio;

  Future<EmergencyStatus> status({String? siteId}) async {
    try {
      final response = await _dio.get(
        ApiEndpoints.emergencyStatus,
        queryParameters: siteId == null ? null : {'site_id': siteId},
      );
      return EmergencyStatus.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  Future<EmergencyRequest> createRequest({
    required EmergencyPositionPayload position,
    required String triggerContext,
    String? siteId,
    String? contactPhone,
    String? note,
  }) async {
    final trimmedContactPhone = _trimmedNonEmpty(contactPhone);
    final trimmedNote = _trimmedNonEmpty(note);
    final data = {
      'trigger_context': triggerContext,
      'metadata': {'source': 'mobile_app'},
      ...position.toJson(),
    };
    if (siteId != null) {
      data['site_id'] = siteId;
    }
    if (trimmedContactPhone != null) {
      data['contact_phone'] = trimmedContactPhone;
    }
    if (trimmedNote != null) {
      data['note'] = trimmedNote;
    }

    try {
      final response = await _dio.post(
        ApiEndpoints.emergencyRequests,
        data: data,
      );
      return EmergencyRequest.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  Future<void> sendLocation({
    required String requestId,
    required EmergencyPositionPayload position,
  }) async {
    try {
      await _dio.post(
        ApiEndpoints.emergencyLocation(requestId),
        data: position.toJson(),
      );
    } on DioException catch (e) {
      throwAppException(e);
    }
  }

  Future<EmergencyRequest> cancel(String requestId) async {
    try {
      final response = await _dio.post(ApiEndpoints.emergencyCancel(requestId));
      return EmergencyRequest.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throwAppException(e);
    }
  }
}

String? _trimmedNonEmpty(String? value) {
  final trimmed = value?.trim();
  return trimmed == null || trimmed.isEmpty ? null : trimmed;
}

class EmergencyLocationService {
  static const LocationSettings _settings = LocationSettings(
    accuracy: LocationAccuracy.high,
    distanceFilter: 15,
  );

  Future<Position> currentPosition() async {
    await _ensurePermission();
    return Geolocator.getCurrentPosition(locationSettings: _settings);
  }

  Stream<Position> positionStream() async* {
    await _ensurePermission();
    yield* Geolocator.getPositionStream(locationSettings: _settings);
  }

  Future<void> _ensurePermission() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw const EmergencyLocationException(
        'Turn on location services to send an emergency request.',
      );
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      throw const EmergencyLocationException(
        'Location permission is required for emergency patrol support.',
      );
    }
    if (permission == LocationPermission.deniedForever) {
      throw const EmergencyLocationException(
        'Location permission is blocked. Enable it in system settings.',
      );
    }
  }
}

class EmergencyState {
  const EmergencyState({
    this.activeRequest,
    this.isSending = false,
    this.isCancelling = false,
    this.lastError,
    this.lastLocationSentAt,
  });

  final EmergencyRequest? activeRequest;
  final bool isSending;
  final bool isCancelling;
  final String? lastError;
  final DateTime? lastLocationSentAt;

  bool get hasActiveRequest => activeRequest?.isActive == true;

  EmergencyState copyWith({
    EmergencyRequest? activeRequest,
    bool clearActiveRequest = false,
    bool? isSending,
    bool? isCancelling,
    String? lastError,
    bool clearError = false,
    DateTime? lastLocationSentAt,
  }) {
    return EmergencyState(
      activeRequest: clearActiveRequest
          ? null
          : activeRequest ?? this.activeRequest,
      isSending: isSending ?? this.isSending,
      isCancelling: isCancelling ?? this.isCancelling,
      lastError: clearError ? null : lastError ?? this.lastError,
      lastLocationSentAt: lastLocationSentAt ?? this.lastLocationSentAt,
    );
  }
}

class EmergencyController extends StateNotifier<EmergencyState> {
  EmergencyController({
    required EmergencyRepository repository,
    required EmergencyLocationService locationService,
  }) : _repository = repository,
       _locationService = locationService,
       super(const EmergencyState());

  final EmergencyRepository _repository;
  final EmergencyLocationService _locationService;
  StreamSubscription<Position>? _positionSubscription;

  Future<void> trigger({
    required String triggerContext,
    String? siteId,
    String? contactPhone,
    String? note,
  }) async {
    if (state.isSending || state.hasActiveRequest) return;
    state = state.copyWith(isSending: true, clearError: true);
    try {
      final position = EmergencyPositionPayload.fromPosition(
        await _locationService.currentPosition(),
      );
      final request = await _repository.createRequest(
        position: position,
        triggerContext: triggerContext,
        siteId: siteId,
        contactPhone: contactPhone,
        note: note,
      );
      state = state.copyWith(
        activeRequest: request,
        isSending: false,
        lastLocationSentAt: DateTime.now(),
      );
      _startLocationUpdates(request.id);
    } catch (e) {
      state = state.copyWith(isSending: false, lastError: _messageFor(e));
      rethrow;
    }
  }

  Future<void> cancel() async {
    final request = state.activeRequest;
    if (request == null || state.isCancelling) return;
    state = state.copyWith(isCancelling: true, clearError: true);
    try {
      await _repository.cancel(request.id);
      await _stopLocationUpdates();
      state = state.copyWith(isCancelling: false, clearActiveRequest: true);
    } catch (e) {
      state = state.copyWith(isCancelling: false, lastError: _messageFor(e));
      rethrow;
    }
  }

  void clearError() {
    state = state.copyWith(clearError: true);
  }

  void _startLocationUpdates(String requestId) {
    _positionSubscription?.cancel();
    _positionSubscription = _locationService.positionStream().listen(
      (position) async {
        try {
          await _repository.sendLocation(
            requestId: requestId,
            position: EmergencyPositionPayload.fromPosition(position),
          );
          state = state.copyWith(lastLocationSentAt: DateTime.now());
        } catch (e) {
          state = state.copyWith(lastError: _messageFor(e));
        }
      },
      onError: (Object error) {
        state = state.copyWith(lastError: _messageFor(error));
      },
    );
  }

  Future<void> _stopLocationUpdates() async {
    await _positionSubscription?.cancel();
    _positionSubscription = null;
  }

  String _messageFor(Object error) {
    if (error is ApiException) return error.message;
    if (error is NetworkException) return error.message;
    if (error is EmergencyLocationException) return error.message;
    return error.toString();
  }

  @override
  void dispose() {
    _positionSubscription?.cancel();
    super.dispose();
  }
}

class EmergencyLocationException implements Exception {
  const EmergencyLocationException(this.message);
  final String message;

  @override
  String toString() => message;
}
