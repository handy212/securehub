import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../data/client_guarding_api.dart';
import '../models/client_guarding_models.dart';
import '../providers/client_guarding_provider.dart';
import '../widgets/client_metric_card.dart';

class ClientGuardingScreen extends ConsumerWidget {
  const ClientGuardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshotAsync = ref.watch(clientGuardingSnapshotProvider);

    return Scaffold(
      backgroundColor: AppTheme.surface,
      body: snapshotAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => _ErrorState(
          message: err.toString(),
          onRetry: () => ref.invalidate(clientGuardingSnapshotProvider),
        ),
        data: (snapshot) => RefreshIndicator(
          onRefresh: () => ref.refresh(clientGuardingSnapshotProvider.future),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 40),
            children: [
              _DashboardHeader(counts: snapshot.counts),
              const SizedBox(height: 32),
              
              _Section(
                title: 'ON-SITE SECURITY',
                subtitle: 'Active Guard Profiles & Coverage',
                child: snapshot.knownGuards.isEmpty
                    ? const _EmptyState(text: 'No active guard profiles.', icon: Icons.badge_outlined)
                    : Column(
                        children: snapshot.knownGuards.map((g) => _KnownGuardTile(guard: g)).toList(),
                      ),
              ),
              const SizedBox(height: 24),
              
              _Section(
                title: 'OPERATIONAL REPORTS',
                subtitle: 'Field Observations & Incidents',
                child: snapshot.reports.isEmpty
                    ? const _EmptyState(text: 'No reports to review.', icon: Icons.description_outlined)
                    : Column(
                        children: snapshot.reports.map((r) => _ReportTile(report: r)).toList(),
                      ),
              ),
              const SizedBox(height: 24),
              
              _Section(
                title: 'PATROL PROOF',
                subtitle: 'Verified Round Totals',
                child: snapshot.patrolRounds.isEmpty
                    ? const _EmptyState(text: 'No active rounds.', icon: Icons.route_rounded)
                    : Column(
                        children: snapshot.patrolRounds.map((r) => _PatrolTile(round: r)).toList(),
                      ),
              ),
              const SizedBox(height: 24),
              
              _Section(
                title: 'ATTENDANCE LOG',
                subtitle: 'Recent Shift Assignments',
                child: snapshot.assignments.isEmpty
                    ? const _EmptyState(text: 'No attendance logs.', icon: Icons.event_note_rounded)
                    : Column(
                        children: snapshot.assignments.map((a) => _AssignmentTile(assignment: a)).toList(),
                      ),
              ),
              const SizedBox(height: 24),
              
              _Section(
                title: 'PORTAL PERMISSIONS',
                subtitle: 'Site Access Summary',
                child: snapshot.access.isEmpty
                    ? const _EmptyState(text: 'No access permissions.', icon: Icons.lock_outline)
                    : Column(
                        children: snapshot.access.map((a) => _AccessTile(access: a)).toList(),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardHeader extends StatelessWidget {
  const _DashboardHeader({required this.counts});
  final ClientGuardingCounts counts;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'EXECUTIVE SUMMARY',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: AppTheme.onSurfaceVariant,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.2,
              ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: ClientMetricCard(label: 'Sites', value: counts.sites, icon: Icons.location_city_rounded)),
            const SizedBox(width: 12),
            Expanded(child: ClientMetricCard(label: 'Reports', value: counts.reports, icon: Icons.description_rounded)),
            const SizedBox(width: 12),
            Expanded(child: ClientMetricCard(label: 'Patrols', value: counts.patrols, icon: Icons.route_rounded)),
            const SizedBox(width: 12),
            Expanded(child: ClientMetricCard(label: 'Guards', value: counts.guards, icon: Icons.security_rounded)),
          ],
        ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.subtitle, required this.child});
  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: AppTheme.onSurfaceVariant,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.2,
                      ),
                ),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
                        fontWeight: FontWeight.w500,
                      ),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: 12),
        Container(
          decoration: BoxDecoration(
            color: AppTheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: AppTheme.outlineVariant.withValues(alpha: 0.1)),
            boxShadow: AppTheme.cardShadow,
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: child,
          ),
        ),
      ],
    );
  }
}

class _KnownGuardTile extends StatelessWidget {
  const _KnownGuardTile({required this.guard});
  final ClientKnownGuard guard;

  @override
  Widget build(BuildContext context) {
    return _ModernTile(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(guard.guardName, style: _titleStyle),
              ),
              _StatusPill(guard.assignmentStatus),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${guard.employeeNumber} · ${guard.guardStatus}',
            style: _metaStyle,
          ),
          const SizedBox(height: 12),
          _InfoRow(icon: Icons.location_on_rounded, text: '${guard.siteName} · ${guard.postName}'),
          const SizedBox(height: 4),
          _InfoRow(icon: Icons.access_time_filled_rounded, text: _range(guard.startsAt, guard.endsAt)),
          if (guard.verifiedCredentials.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: guard.verifiedCredentials.map((c) => _CredentialChip(label: c)).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReportTile extends ConsumerWidget {
  const _ReportTile({required this.report});
  final ClientGuardingReport report;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _ModernTile(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(report.title, style: _titleStyle)),
              _StatusPill('${report.acknowledgementCount} ACK'),
            ],
          ),
          const SizedBox(height: 4),
          Text('${report.siteName} · ${report.postName}', style: _metaStyle),
          if (report.body.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              report.body,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: _bodyStyle,
            ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              Text(report.guardName.isNotEmpty ? report.guardName : report.reportType, style: _metaStyle.copyWith(fontWeight: FontWeight.w700)),
              const Spacer(),
              Text(_dateLabel(report.submittedAt), style: _metaStyle),
            ],
          ),
          if (report.canAcknowledge) ...[
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.tonal(
                style: FilledButton.styleFrom(
                  backgroundColor: AppTheme.secondary.withValues(alpha: 0.1),
                  foregroundColor: AppTheme.secondary,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
                onPressed: () => _handleAcknowledge(context, ref, report.id),
                child: const Text('ACKNOWLEDGE REPORT'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _handleAcknowledge(BuildContext context, WidgetRef ref, String reportId) async {
    final comment = await _askForAcknowledgementComment(context);
    if (comment == null) return;
    
    try {
      await ref.read(clientGuardingApiProvider).acknowledgeReport(reportId, comment: comment);
      ref.invalidate(clientGuardingSnapshotProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Report Acknowledged')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
      }
    }
  }
}

class _PatrolTile extends StatelessWidget {
  const _PatrolTile({required this.round});
  final ClientGuardingPatrolRound round;

  @override
  Widget build(BuildContext context) {
    return _ModernTile(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(round.routeName, style: _titleStyle)),
              _StatusPill(round.status),
            ],
          ),
          const SizedBox(height: 12),
          _InfoRow(icon: Icons.location_on_rounded, text: '${round.siteName} · ${round.postName}'),
          const SizedBox(height: 4),
          _InfoRow(icon: Icons.qr_code_scanner_rounded, text: '${round.scanCount} Checkpoints Verified'),
          const SizedBox(height: 12),
          Row(
            children: [
              Text(round.guardName.isEmpty ? 'Scheduled' : round.guardName, style: _metaStyle.copyWith(fontWeight: FontWeight.w700)),
              const Spacer(),
              Text(_dateLabel(round.scheduledStart), style: _metaStyle),
            ],
          ),
        ],
      ),
    );
  }
}

class _AssignmentTile extends StatelessWidget {
  const _AssignmentTile({required this.assignment});
  final ClientGuardingAssignment assignment;

  @override
  Widget build(BuildContext context) {
    return _ModernTile(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(assignment.guardName, style: _titleStyle)),
              _StatusPill(assignment.status),
            ],
          ),
          const SizedBox(height: 12),
          _InfoRow(icon: Icons.location_on_rounded, text: '${assignment.siteName} · ${assignment.postName}'),
          const SizedBox(height: 4),
          _InfoRow(icon: Icons.access_time_filled_rounded, text: _range(assignment.startsAt, assignment.endsAt)),
        ],
      ),
    );
  }
}

class _AccessTile extends StatelessWidget {
  const _AccessTile({required this.access});
  final ClientGuardingAccess access;

  @override
  Widget build(BuildContext context) {
    final labels = <String>[
      if (access.canViewReports) 'Reports',
      if (access.canViewPatrols) 'Patrols',
      if (access.canViewAttendance) 'Attendance',
      if (access.canViewGuards) 'Profiles',
      if (access.canAcknowledgeReports) 'Acknowledgement',
    ];
    
    return _ModernTile(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(access.siteName, style: _titleStyle),
          const SizedBox(height: 4),
          Text('Role: ${access.role.toUpperCase()}', style: _metaStyle),
          const SizedBox(height: 12),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: labels.map((l) => _AccessChip(label: l)).toList(),
          ),
        ],
      ),
    );
  }
}

class _ModernTile extends StatelessWidget {
  const _ModernTile({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: child,
        ),
        const Divider(height: 1, indent: 16, endIndent: 16),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 14, color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6)),
        const SizedBox(width: 8),
        Expanded(child: Text(text, style: _metaStyle)),
      ],
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill(this.label);
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(100),
      ),
      child: Text(
        label.toUpperCase(),
        style: const TextStyle(
          color: AppTheme.onSurface,
          fontSize: 10,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _CredentialChip extends StatelessWidget {
  const _CredentialChip({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.secondary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppTheme.secondary.withValues(alpha: 0.1)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.verified_user_rounded, size: 10, color: AppTheme.secondary),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(color: AppTheme.secondary, fontSize: 10, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}

class _AccessChip extends StatelessWidget {
  const _AccessChip({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.onSurfaceVariant.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: AppTheme.onSurfaceVariant.withValues(alpha: 0.8),
          fontSize: 10,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.text, required this.icon});
  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Center(
        child: Column(
          children: [
            Icon(icon, size: 32, color: AppTheme.outlineVariant.withValues(alpha: 0.2)),
            const SizedBox(height: 12),
            Text(text, textAlign: TextAlign.center, style: _metaStyle),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline_rounded, size: 48, color: AppTheme.error),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center, style: _metaStyle),
            const SizedBox(height: 24),
            FilledButton(onPressed: onRetry, child: const Text('Retry Connection')),
          ],
        ),
      ),
    );
  }
}

Future<String?> _askForAcknowledgementComment(BuildContext context) async {
  final controller = TextEditingController();
  try {
    return await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Acknowledge Report'),
          content: TextField(
            controller: controller,
            autofocus: true,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Operational Comment',
              hintText: 'Add a note (optional)...',
              fillColor: AppTheme.surfaceContainerLow,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(controller.text.trim()),
              child: const Text('Confirm Ack'),
            ),
          ],
        );
      },
    );
  } finally {
    controller.dispose();
  }
}

TextStyle get _titleStyle => const TextStyle(
  color: AppTheme.primary,
  fontSize: 15,
  fontWeight: FontWeight.w800,
  letterSpacing: -0.3,
);

TextStyle get _metaStyle => TextStyle(
  color: AppTheme.onSurfaceVariant.withValues(alpha: 0.7),
  fontSize: 12,
  fontWeight: FontWeight.w600,
);

TextStyle get _bodyStyle => TextStyle(
  color: AppTheme.onSurface.withValues(alpha: 0.8),
  fontSize: 13,
  fontWeight: FontWeight.w400,
  height: 1.4,
);

String _range(DateTime? start, DateTime? end) {
  if (start == null) return 'Not available';
  if (end == null) return _dateLabel(start);
  return '${_dateLabel(start)} - ${_timeLabel(end)}';
}

String _dateLabel(DateTime? date) {
  if (date == null) return '--/-- --:--';
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(date.day)}/${two(date.month)} ${two(date.hour)}:${two(date.minute)}';
}

String _timeLabel(DateTime date) {
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(date.hour)}:${two(date.minute)}';
}
