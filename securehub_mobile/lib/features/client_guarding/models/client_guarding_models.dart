class ClientGuardingSnapshot {
  const ClientGuardingSnapshot({
    required this.counts,
    required this.access,
    required this.reports,
    required this.patrolRounds,
    required this.assignments,
    required this.knownGuards,
  });

  final ClientGuardingCounts counts;
  final List<ClientGuardingAccess> access;
  final List<ClientGuardingReport> reports;
  final List<ClientGuardingPatrolRound> patrolRounds;
  final List<ClientGuardingAssignment> assignments;
  final List<ClientKnownGuard> knownGuards;

  factory ClientGuardingSnapshot.fromJson(Map<String, dynamic> json) {
    return ClientGuardingSnapshot(
      counts: ClientGuardingCounts.fromJson(
        Map<String, dynamic>.from(json['counts'] as Map? ?? const {}),
      ),
      access: _list(json['access'], ClientGuardingAccess.fromJson),
      reports: _list(json['reports'], ClientGuardingReport.fromJson),
      patrolRounds: _list(
        json['patrol_rounds'],
        ClientGuardingPatrolRound.fromJson,
      ),
      assignments: _list(
        json['assignments'],
        ClientGuardingAssignment.fromJson,
      ),
      knownGuards: _list(json['known_guards'], ClientKnownGuard.fromJson),
    );
  }
}

class ClientGuardingCounts {
  const ClientGuardingCounts({
    this.sites = 0,
    this.reports = 0,
    this.patrols = 0,
    this.assignments = 0,
    this.guards = 0,
  });

  final int sites;
  final int reports;
  final int patrols;
  final int assignments;
  final int guards;

  factory ClientGuardingCounts.fromJson(Map<String, dynamic> json) {
    return ClientGuardingCounts(
      sites: _int(json['sites']),
      reports: _int(json['reports']),
      patrols: _int(json['patrols']),
      assignments: _int(json['assignments']),
      guards: _int(json['guards']),
    );
  }
}

class ClientGuardingAccess {
  const ClientGuardingAccess({
    required this.siteId,
    required this.siteName,
    required this.role,
    this.canViewReports = false,
    this.canViewPatrols = false,
    this.canViewAttendance = false,
    this.canViewGuards = false,
    this.canAcknowledgeReports = false,
  });

  final String siteId;
  final String siteName;
  final String role;
  final bool canViewReports;
  final bool canViewPatrols;
  final bool canViewAttendance;
  final bool canViewGuards;
  final bool canAcknowledgeReports;

  factory ClientGuardingAccess.fromJson(Map<String, dynamic> json) {
    return ClientGuardingAccess(
      siteId: json['site_id']?.toString() ?? '',
      siteName: json['site_name']?.toString() ?? 'Site',
      role: json['role']?.toString() ?? 'viewer',
      canViewReports: json['can_view_reports'] == true,
      canViewPatrols: json['can_view_patrols'] == true,
      canViewAttendance: json['can_view_attendance'] == true,
      canViewGuards: json['can_view_guards'] == true,
      canAcknowledgeReports: json['can_acknowledge_reports'] == true,
    );
  }
}

class ClientGuardingReport {
  const ClientGuardingReport({
    required this.id,
    required this.title,
    required this.reportType,
    required this.body,
    required this.siteName,
    required this.postName,
    required this.guardName,
    this.submittedAt,
    this.acknowledgementCount = 0,
    this.canAcknowledge = false,
  });

  final String id;
  final String title;
  final String reportType;
  final String body;
  final String siteName;
  final String postName;
  final String guardName;
  final DateTime? submittedAt;
  final int acknowledgementCount;
  final bool canAcknowledge;

  factory ClientGuardingReport.fromJson(Map<String, dynamic> json) {
    return ClientGuardingReport(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Report',
      reportType: json['report_type']?.toString() ?? '',
      body: json['body']?.toString() ?? '',
      siteName: json['site_name']?.toString() ?? '',
      postName: json['post_name']?.toString() ?? '',
      guardName: json['guard_name']?.toString() ?? '',
      submittedAt: _date(json['submitted_at']),
      acknowledgementCount: _int(json['acknowledgement_count']),
      canAcknowledge: json['can_acknowledge'] == true,
    );
  }
}

class ClientKnownGuard {
  const ClientKnownGuard({
    required this.assignmentId,
    required this.guardName,
    required this.employeeNumber,
    required this.guardStatus,
    required this.siteName,
    required this.postName,
    required this.assignmentStatus,
    this.startsAt,
    this.endsAt,
    this.verifiedCredentials = const [],
  });

  final String assignmentId;
  final String guardName;
  final String employeeNumber;
  final String guardStatus;
  final String siteName;
  final String postName;
  final String assignmentStatus;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final List<String> verifiedCredentials;

  factory ClientKnownGuard.fromJson(Map<String, dynamic> json) {
    return ClientKnownGuard(
      assignmentId: json['assignment_id']?.toString() ?? '',
      guardName: json['guard_name']?.toString() ?? 'Guard',
      employeeNumber: json['employee_number']?.toString() ?? '',
      guardStatus: json['guard_status']?.toString() ?? '',
      siteName: json['site_name']?.toString() ?? '',
      postName: json['post_name']?.toString() ?? '',
      assignmentStatus: json['assignment_status']?.toString() ?? '',
      startsAt: _date(json['starts_at']),
      endsAt: _date(json['ends_at']),
      verifiedCredentials: (json['verified_credentials'] as List? ?? const [])
          .map((item) => item.toString())
          .toList(),
    );
  }
}

class ClientGuardingPatrolRound {
  const ClientGuardingPatrolRound({
    required this.id,
    required this.routeName,
    required this.siteName,
    required this.postName,
    required this.guardName,
    required this.status,
    this.scanCount = 0,
    this.scheduledStart,
  });

  final String id;
  final String routeName;
  final String siteName;
  final String postName;
  final String guardName;
  final String status;
  final int scanCount;
  final DateTime? scheduledStart;

  factory ClientGuardingPatrolRound.fromJson(Map<String, dynamic> json) {
    return ClientGuardingPatrolRound(
      id: json['id']?.toString() ?? '',
      routeName: json['route_name']?.toString() ?? 'Route',
      siteName: json['site_name']?.toString() ?? '',
      postName: json['post_name']?.toString() ?? '',
      guardName: json['guard_name']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      scanCount: _int(json['scan_count']),
      scheduledStart: _date(json['scheduled_start']),
    );
  }
}

class ClientGuardingAssignment {
  const ClientGuardingAssignment({
    required this.id,
    required this.guardName,
    required this.siteName,
    required this.postName,
    required this.status,
    this.startsAt,
    this.endsAt,
  });

  final String id;
  final String guardName;
  final String siteName;
  final String postName;
  final String status;
  final DateTime? startsAt;
  final DateTime? endsAt;

  factory ClientGuardingAssignment.fromJson(Map<String, dynamic> json) {
    return ClientGuardingAssignment(
      id: json['id']?.toString() ?? '',
      guardName: json['guard_name']?.toString() ?? 'Guard',
      siteName: json['site_name']?.toString() ?? '',
      postName: json['post_name']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      startsAt: _date(json['starts_at']),
      endsAt: _date(json['ends_at']),
    );
  }
}

List<T> _list<T>(dynamic value, T Function(Map<String, dynamic>) fromJson) {
  return (value as List? ?? const [])
      .map((item) => fromJson(Map<String, dynamic>.from(item as Map)))
      .toList();
}

DateTime? _date(dynamic value) =>
    value == null ? null : DateTime.tryParse(value.toString());

int _int(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}
