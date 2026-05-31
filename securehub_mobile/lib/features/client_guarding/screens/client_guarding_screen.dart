import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../data/client_guarding_api.dart';
import '../models/client_guarding_models.dart';
import '../providers/client_guarding_provider.dart';

class ClientGuardingScreen extends ConsumerWidget {
  const ClientGuardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshotAsync = ref.watch(clientGuardingSnapshotProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: snapshotAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => _ErrorState(
          message: err.toString(),
          onRetry: () => ref.invalidate(clientGuardingSnapshotProvider),
        ),
        data: (snapshot) => RefreshIndicator(
          onRefresh: () => ref.refresh(clientGuardingSnapshotProvider.future),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              _SummaryStrip(counts: snapshot.counts),
              const SizedBox(height: 12),
              _Section(
                title: 'Know your guard',
                subtitle: 'Current and upcoming coverage',
                trailing: '${snapshot.counts.guards} visible',
                child: snapshot.knownGuards.isEmpty
                    ? const _EmptyText('No current or upcoming guard profiles.')
                    : Column(
                        children: [
                          for (final guard in snapshot.knownGuards)
                            _KnownGuardTile(guard: guard),
                        ],
                      ),
              ),
              const SizedBox(height: 12),
              _Section(
                title: 'Approved reports',
                subtitle: 'Released client-visible reports',
                trailing: '${snapshot.counts.reports} rows',
                child: snapshot.reports.isEmpty
                    ? const _EmptyText('No approved reports.')
                    : Column(
                        children: [
                          for (final report in snapshot.reports)
                            _ReportTile(report: report),
                        ],
                      ),
              ),
              const SizedBox(height: 12),
              _Section(
                title: 'Patrol proof',
                subtitle: 'Rounds and checkpoint totals',
                child: snapshot.patrolRounds.isEmpty
                    ? const _EmptyText('No patrol rounds visible.')
                    : Column(
                        children: [
                          for (final round in snapshot.patrolRounds)
                            _PatrolTile(round: round),
                        ],
                      ),
              ),
              const SizedBox(height: 12),
              _Section(
                title: 'Attendance',
                subtitle: 'Visible shift assignments',
                child: snapshot.assignments.isEmpty
                    ? const _EmptyText('No attendance visible.')
                    : Column(
                        children: [
                          for (final assignment in snapshot.assignments)
                            _AssignmentTile(assignment: assignment),
                        ],
                      ),
              ),
              const SizedBox(height: 12),
              _Section(
                title: 'Site access',
                subtitle: 'Enabled portal permissions',
                child: snapshot.access.isEmpty
                    ? const _EmptyText('No guarding site access.')
                    : Column(
                        children: [
                          for (final access in snapshot.access)
                            _AccessTile(access: access),
                        ],
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryStrip extends StatelessWidget {
  const _SummaryStrip({required this.counts});

  final ClientGuardingCounts counts;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: _panelDecoration(),
      child: Row(
        children: [
          _Metric(label: 'Sites', value: counts.sites),
          _Metric(label: 'Reports', value: counts.reports),
          _Metric(label: 'Patrols', value: counts.patrols),
          _Metric(label: 'Guards', value: counts.guards),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: AppTheme.onSurfaceVariant.withValues(alpha: 0.72),
              fontSize: 10,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            '$value',
            style: const TextStyle(
              color: AppTheme.primary,
              fontSize: 20,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.subtitle,
    required this.child,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final String? trailing;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 9),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: AppTheme.primary,
                          fontSize: 14,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        subtitle,
                        style: TextStyle(
                          color: AppTheme.onSurfaceVariant.withValues(
                            alpha: 0.7,
                          ),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                if (trailing != null) _StatusPill(trailing!),
              ],
            ),
          ),
          Divider(
            height: 1,
            color: AppTheme.outlineVariant.withValues(alpha: 0.16),
          ),
          child,
        ],
      ),
    );
  }
}

class _KnownGuardTile extends StatelessWidget {
  const _KnownGuardTile({required this.guard});

  final ClientKnownGuard guard;

  @override
  Widget build(BuildContext context) {
    return _TileShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(guard.guardName, style: _titleStyle),
                    const SizedBox(height: 2),
                    Text(
                      '${guard.employeeNumber} · ${guard.guardStatus}',
                      style: _metaStyle,
                    ),
                  ],
                ),
              ),
              _StatusPill(guard.assignmentStatus),
            ],
          ),
          const SizedBox(height: 8),
          _CompactLine(
            left: '${guard.siteName} · ${guard.postName}',
            right: _range(guard.startsAt, guard.endsAt),
          ),
          if (guard.verifiedCredentials.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final credential in guard.verifiedCredentials)
                  _StatusPill(credential, tone: _PillTone.green),
              ],
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
    return _TileShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(report.title, style: _titleStyle),
                    const SizedBox(height: 2),
                    Text(
                      '${report.siteName} · ${report.postName}',
                      style: _metaStyle,
                    ),
                  ],
                ),
              ),
              _StatusPill('${report.acknowledgementCount} ack'),
            ],
          ),
          if (report.body.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              report.body,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: _metaStyle,
            ),
          ],
          const SizedBox(height: 8),
          _CompactLine(
            left: report.guardName.isNotEmpty
                ? report.guardName
                : report.reportType,
            right: _dateLabel(report.submittedAt),
          ),
          if (report.canAcknowledge) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () async {
                  final comment = await _askForAcknowledgementComment(context);
                  if (comment == null) return;
                  await ref
                      .read(clientGuardingApiProvider)
                      .acknowledgeReport(report.id, comment: comment);
                  ref.invalidate(clientGuardingSnapshotProvider);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Report acknowledged')),
                    );
                  }
                },
                icon: const Icon(Icons.check_circle_outline, size: 16),
                label: const Text('Acknowledge'),
              ),
            ),
          ],
        ],
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
          title: const Text('Acknowledge report'),
          content: TextField(
            controller: controller,
            autofocus: true,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Comment',
              hintText: 'Optional note for operations',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () =>
                  Navigator.of(dialogContext).pop(controller.text.trim()),
              child: const Text('Acknowledge'),
            ),
          ],
        );
      },
    );
  } finally {
    controller.dispose();
  }
}

class _PatrolTile extends StatelessWidget {
  const _PatrolTile({required this.round});

  final ClientGuardingPatrolRound round;

  @override
  Widget build(BuildContext context) {
    return _TileShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(round.routeName, style: _titleStyle),
          const SizedBox(height: 4),
          _CompactLine(
            left: '${round.siteName} · ${round.postName}',
            right: '${round.scanCount} scans',
          ),
          const SizedBox(height: 6),
          _CompactLine(
            left: round.guardName.isEmpty ? round.status : round.guardName,
            right: _dateLabel(round.scheduledStart),
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
    return _TileShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(assignment.guardName, style: _titleStyle)),
              _StatusPill(assignment.status),
            ],
          ),
          const SizedBox(height: 6),
          _CompactLine(
            left: '${assignment.siteName} · ${assignment.postName}',
            right: _range(assignment.startsAt, assignment.endsAt),
          ),
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
      if (access.canViewGuards) 'Know your guard',
      if (access.canAcknowledgeReports) 'Ack reports',
    ];
    return _TileShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(access.siteName, style: _titleStyle),
          const SizedBox(height: 7),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final label in labels)
                _StatusPill(
                  label,
                  tone: label == 'Know your guard'
                      ? _PillTone.green
                      : _PillTone.neutral,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TileShell extends StatelessWidget {
  const _TileShell({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      child: child,
    );
  }
}

class _CompactLine extends StatelessWidget {
  const _CompactLine({required this.left, required this.right});

  final String left;
  final String right;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(left, style: _metaStyle, overflow: TextOverflow.ellipsis),
        ),
        const SizedBox(width: 8),
        Text(right, style: _metaStyle),
      ],
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill(this.label, {this.tone = _PillTone.neutral});

  final String label;
  final _PillTone tone;

  @override
  Widget build(BuildContext context) {
    final color = switch (tone) {
      _PillTone.green => AppTheme.secondary,
      _PillTone.neutral => AppTheme.onSurfaceVariant,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.16)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _EmptyText extends StatelessWidget {
  const _EmptyText(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(18),
      child: Center(
        child: Text(text, textAlign: TextAlign.center, style: _metaStyle),
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
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.security_update_warning_outlined, size: 42),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center, style: _metaStyle),
            const SizedBox(height: 14),
            FilledButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

enum _PillTone { neutral, green }

BoxDecoration _panelDecoration() {
  return BoxDecoration(
    color: AppTheme.surfaceContainerLowest,
    borderRadius: BorderRadius.circular(18),
    border: Border.all(color: AppTheme.outlineVariant.withValues(alpha: 0.14)),
    boxShadow: AppTheme.cardShadow,
  );
}

TextStyle get _titleStyle => const TextStyle(
  color: AppTheme.primary,
  fontSize: 13,
  fontWeight: FontWeight.w800,
);

TextStyle get _metaStyle => TextStyle(
  color: AppTheme.onSurfaceVariant.withValues(alpha: 0.72),
  fontSize: 11,
  fontWeight: FontWeight.w600,
);

String _range(DateTime? start, DateTime? end) {
  if (start == null) return '';
  if (end == null) return _dateLabel(start);
  return '${_dateLabel(start)} - ${_timeLabel(end)}';
}

String _dateLabel(DateTime? date) {
  if (date == null) return '';
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(date.day)}/${two(date.month)} ${two(date.hour)}:${two(date.minute)}';
}

String _timeLabel(DateTime date) {
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(date.hour)}:${two(date.minute)}';
}
