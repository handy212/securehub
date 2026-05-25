import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../data/guard_api.dart';
import '../models/guard_models.dart';

final guardShiftsProvider =
    FutureProvider.autoDispose<List<GuardShiftAssignment>>((ref) async {
  final api = ref.watch(guardApiProvider);
  await api.flushOfflineQueue();
  return api.fetchShifts();
});

final guardPatrolRoundsProvider =
    FutureProvider.autoDispose<List<GuardPatrolRound>>((ref) async {
  return ref.watch(guardApiProvider).fetchPatrolRounds();
});

final guardDispatchProvider =
    FutureProvider.autoDispose<List<GuardDispatchTask>>((ref) async {
  return ref.watch(guardApiProvider).fetchDispatchTasks();
});

final guardWelfareChecksProvider =
    FutureProvider.autoDispose<List<GuardWelfareCheck>>((ref) async {
  return ref.watch(guardApiProvider).fetchWelfareChecks();
});

/// Pending welfare checks that need attention (overdue or due within 30 minutes).
final guardUrgentWelfareProvider = Provider<List<GuardWelfareCheck>>((ref) {
  final checks = ref.watch(guardWelfareChecksProvider).valueOrNull ?? const [];
  return checks.where((c) => c.isPending && (c.isOverdue || c.isDueSoon)).toList();
});

/// Active assignment for location pings / panic context.
final guardActiveAssignmentProvider = Provider<GuardShiftAssignment?>((ref) {
  final shifts = ref.watch(guardShiftsProvider).valueOrNull ?? const [];
  for (final shift in shifts) {
    if (shift.isClockedIn) return shift;
  }
  return shifts.isNotEmpty ? shifts.first : null;
});

Future<Position?> readGuardPosition() async {
  if (!await Geolocator.isLocationServiceEnabled()) return null;
  var permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }
  if (permission == LocationPermission.denied ||
      permission == LocationPermission.deniedForever) {
    return null;
  }
  return Geolocator.getCurrentPosition();
}
