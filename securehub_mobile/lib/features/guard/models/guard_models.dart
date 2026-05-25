/// Typed models for guard mobile API responses.

class GuardShiftAssignment {
  const GuardShiftAssignment({
    required this.id,
    required this.status,
    required this.postName,
    required this.siteName,
    this.startsAt,
    this.endsAt,
    this.shiftId,
  });

  final String id;
  final String status;
  final String postName;
  final String siteName;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final String? shiftId;

  factory GuardShiftAssignment.fromJson(Map<String, dynamic> json) {
    return GuardShiftAssignment(
      id: json['id'] as String,
      status: json['status'] as String? ?? 'assigned',
      postName: json['post_name'] as String? ?? 'Post',
      siteName: json['site_name'] as String? ?? 'Site',
      startsAt: _parseDate(json['starts_at']),
      endsAt: _parseDate(json['ends_at']),
      shiftId: json['shift'] as String?,
    );
  }

  bool get isClockedIn => status == 'clocked_in';
  bool get canClockIn => status == 'accepted';
  bool get canClockOut => status == 'clocked_in';
  bool get canAccept => status == 'assigned';

  String get displayTitle => '$siteName — $postName';

  String get statusLabel => status.replaceAll('_', ' ');
}

class GuardPatrolCheckpoint {
  const GuardPatrolCheckpoint({
    required this.id,
    required this.name,
    required this.code,
    required this.sequence,
  });

  final String id;
  final String name;
  final String code;
  final int sequence;

  factory GuardPatrolCheckpoint.fromJson(Map<String, dynamic> json) {
    return GuardPatrolCheckpoint(
      id: (json['checkpoint'] ?? json['checkpoint_id'] ?? '').toString(),
      name: json['checkpoint_name'] as String? ?? 'Checkpoint',
      code: json['checkpoint_code'] as String? ?? '',
      sequence: json['sequence'] as int? ?? 0,
    );
  }
}

class GuardPatrolRoute {
  const GuardPatrolRoute({
    required this.id,
    required this.name,
    required this.checkpoints,
  });

  final String id;
  final String name;
  final List<GuardPatrolCheckpoint> checkpoints;

  factory GuardPatrolRoute.fromJson(Map<String, dynamic> json) {
    final rawCheckpoints = json['route_checkpoints'] as List<dynamic>? ?? [];
    final checkpoints = rawCheckpoints
        .map((item) => GuardPatrolCheckpoint.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList()
      ..sort((a, b) => a.sequence.compareTo(b.sequence));
    return GuardPatrolRoute(
      id: json['id'] as String,
      name: json['name'] as String? ?? 'Route',
      checkpoints: checkpoints,
    );
  }
}

class GuardPatrolRound {
  const GuardPatrolRound({
    required this.id,
    required this.status,
    required this.routeName,
    required this.siteName,
    required this.postName,
    required this.route,
    this.assignmentId,
    this.scheduledStart,
    this.scheduledEnd,
    this.scannedCheckpointIds = const {},
  });

  final String id;
  final String status;
  final String routeName;
  final String siteName;
  final String postName;
  final GuardPatrolRoute route;
  final String? assignmentId;
  final DateTime? scheduledStart;
  final DateTime? scheduledEnd;
  final Set<String> scannedCheckpointIds;

  factory GuardPatrolRound.fromJson(Map<String, dynamic> json) {
    final routeJson = json['route'] as Map<String, dynamic>? ?? {};
    final scans = json['scans'] as List<dynamic>? ?? [];
    final scannedIds = scans
        .map((scan) => (scan as Map)['checkpoint']?.toString())
        .whereType<String>()
        .toSet();

    return GuardPatrolRound(
      id: json['id'] as String,
      status: json['status'] as String? ?? 'scheduled',
      routeName: json['route_name'] as String? ?? routeJson['name'] as String? ?? 'Route',
      siteName: json['site_name'] as String? ?? '',
      postName: json['post_name'] as String? ?? '',
      route: GuardPatrolRoute.fromJson(routeJson),
      assignmentId: json['assignment']?.toString(),
      scheduledStart: _parseDate(json['scheduled_start']),
      scheduledEnd: _parseDate(json['scheduled_end']),
      scannedCheckpointIds: scannedIds,
    );
  }

  bool isComplete(String checkpointId) => scannedCheckpointIds.contains(checkpointId);
}

class GuardDispatchTask {
  const GuardDispatchTask({
    required this.id,
    required this.status,
    required this.priority,
    required this.title,
    required this.description,
    this.siteName,
  });

  final String id;
  final String status;
  final String priority;
  final String title;
  final String description;
  final String? siteName;

  factory GuardDispatchTask.fromJson(Map<String, dynamic> json) {
    return GuardDispatchTask(
      id: json['id'] as String,
      status: json['status'] as String? ?? 'open',
      priority: json['priority'] as String? ?? 'medium',
      title: json['title'] as String? ?? 'Dispatch',
      description: json['description'] as String? ?? '',
      siteName: json['site_name'] as String?,
    );
  }

  String? get nextAction {
    return switch (status) {
      'assigned' => 'accept',
      'accepted' => 'en-route',
      'en_route' => 'arrive',
      'arrived' => 'resolve',
      _ => null,
    };
  }

  String get nextActionLabel {
    return switch (nextAction) {
      'accept' => 'Accept',
      'en-route' => 'En route',
      'arrive' => 'Arrived',
      'resolve' => 'Resolve',
      _ => '',
    };
  }
}

class GuardScanResult {
  const GuardScanResult({
    this.queued = false,
    this.scanId,
    this.checkpointInstructions = '',
    this.postOrders = const [],
  });

  final bool queued;
  final String? scanId;
  final String checkpointInstructions;
  final List<GuardPostOrderSnippet> postOrders;

  factory GuardScanResult.fromJson(Map<String, dynamic> json) {
    final orders = (json['post_orders'] as List<dynamic>? ?? [])
        .map((item) => GuardPostOrderSnippet.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
    return GuardScanResult(
      queued: json['queued'] == true,
      scanId: json['scan_id'] as String?,
      checkpointInstructions: json['checkpoint_instructions'] as String? ?? '',
      postOrders: orders,
    );
  }
}

class GuardPostOrderSnippet {
  const GuardPostOrderSnippet({required this.title, required this.body});

  final String title;
  final String body;

  factory GuardPostOrderSnippet.fromJson(Map<String, dynamic> json) {
    return GuardPostOrderSnippet(
      title: json['title'] as String? ?? 'Post order',
      body: json['body'] as String? ?? '',
    );
  }
}

class GuardWelfareCheck {
  const GuardWelfareCheck({
    required this.id,
    required this.assignmentId,
    required this.status,
    required this.dueAt,
    required this.siteName,
    required this.postName,
    this.isOverdue = false,
    this.responseNote = '',
  });

  final String id;
  final String assignmentId;
  final String status;
  final DateTime dueAt;
  final String siteName;
  final String postName;
  final bool isOverdue;
  final String responseNote;

  factory GuardWelfareCheck.fromJson(Map<String, dynamic> json) {
    return GuardWelfareCheck(
      id: json['id'] as String,
      assignmentId: json['assignment_id'] as String,
      status: json['status'] as String? ?? 'pending',
      dueAt: _parseDate(json['due_at']) ?? DateTime.now(),
      siteName: json['site_name'] as String? ?? '',
      postName: json['post_name'] as String? ?? '',
      isOverdue: json['is_overdue'] as bool? ?? false,
      responseNote: json['response_note'] as String? ?? '',
    );
  }

  bool get isPending => status == 'pending' || status == 'missed';

  bool get isDueSoon {
    if (!isPending) return false;
    final minutes = dueAt.difference(DateTime.now()).inMinutes;
    return minutes >= 0 && minutes <= 30;
  }
}

class GuardFieldReportDraft {
  const GuardFieldReportDraft({
    required this.reportType,
    required this.title,
    required this.body,
    this.assignmentId,
    this.visibleToClient = true,
  });

  final String reportType;
  final String title;
  final String body;
  final String? assignmentId;
  final bool visibleToClient;

  Map<String, dynamic> toJson() {
    return {
      'report_type': reportType,
      'title': title,
      'body': body,
      'status': 'submitted',
      'visible_to_client': visibleToClient,
      if (assignmentId != null) 'assignment': assignmentId,
    };
  }
}

DateTime? _parseDate(dynamic value) {
  if (value == null) return null;
  return DateTime.tryParse(value.toString());
}

List<T> parseGuardList<T>(
  dynamic data,
  T Function(Map<String, dynamic> json) fromJson,
) {
  if (data is List) {
    return data.map((item) => fromJson(Map<String, dynamic>.from(item as Map))).toList();
  }
  if (data is Map && data['results'] is List) {
    return (data['results'] as List)
        .map((item) => fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }
  return [];
}
