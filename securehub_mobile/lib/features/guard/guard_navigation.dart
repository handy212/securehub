/// Maps guarding push payloads to in-app routes.

String? guardRouteFromPushData(Map<String, dynamic> data) {
  final explicitRoute = data['route'] as String?;
  if (explicitRoute != null && explicitRoute.isNotEmpty) {
    if (explicitRoute.startsWith('/guard')) return explicitRoute;
    if (explicitRoute.startsWith('guard/')) return '/$explicitRoute';
  }

  final eventType = data['event_type'] as String? ?? '';
  if (eventType.isEmpty) return '/guard/home';

  if (eventType.contains('panic')) return '/guard/panic';
  if (eventType.contains('dispatch')) return '/guard/dispatch';
  if (eventType.contains('patrol')) return '/guard/patrols';
  if (eventType.contains('welfare')) return '/guard/welfare';
  if (eventType.contains('clock')) return '/guard/home';

  return '/guard/home';
}
