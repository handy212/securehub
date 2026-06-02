import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

GuardShiftAssignment? _resolveReportAssignment(WidgetRef ref) {
  final active = ref.read(guardActiveAssignmentProvider);
  if (active != null) return active;
  final shifts = ref.read(guardShiftsProvider).valueOrNull;
  if (shifts == null || shifts.isEmpty) return null;
  return shifts.first;
}

const _reportTypes = <String, Map<String, dynamic>>{
  'incident': {'label': 'Incident', 'icon': Icons.report_problem_rounded, 'color': AppTheme.error},
  'daily_activity': {'label': 'Daily Activity', 'icon': Icons.event_note_rounded, 'color': AppTheme.secondary},
  'maintenance': {'label': 'Maintenance', 'icon': Icons.build_circle_rounded, 'color': Colors.orange},
  'visitor': {'label': 'Visitor Log', 'icon': Icons.people_alt_rounded, 'color': Colors.blue},
  'parking': {'label': 'Parking Violation', 'icon': Icons.local_parking_rounded, 'color': Colors.indigo},
  'pass_on': {'label': 'Pass-on Note', 'icon': Icons.forward_to_inbox_rounded, 'color': Colors.teal},
  'other': {'label': 'Other', 'icon': Icons.more_horiz_rounded, 'color': AppTheme.onSurfaceVariant},
};

class GuardReportScreen extends ConsumerStatefulWidget {
  const GuardReportScreen({super.key});

  @override
  ConsumerState<GuardReportScreen> createState() => _GuardReportScreenState();
}

class _GuardReportScreenState extends ConsumerState<GuardReportScreen> {
  final _titleController = TextEditingController();
  final _bodyController = TextEditingController();
  String _reportType = 'incident';
  bool _visibleToClient = true;
  bool _submitting = false;

  @override
  void dispose() {
    _titleController.dispose();
    _bodyController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final title = _titleController.text.trim();
    final body = _bodyController.text.trim();
    if (title.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Report title is required')));
      return;
    }

    final assignment = _resolveReportAssignment(ref);
    if (assignment == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Select an assignment first')));
      return;
    }

    setState(() => _submitting = true);
    try {
      await ref.read(guardApiProvider).submitFieldReport(
            GuardFieldReportDraft(
              reportType: _reportType,
              title: title,
              body: body,
              assignmentId: assignment.id,
              visibleToClient: _visibleToClient,
            ),
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Field Report Submitted Successfully')));
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Submission failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final assignment = ref.watch(guardActiveAssignmentProvider);

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: const Text('New Field Report'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (assignment != null)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceContainerLowest,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.outlineVariant.withValues(alpha: 0.1)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.link_rounded, color: AppTheme.secondary),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'LINKED TO ASSIGNMENT',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: AppTheme.onSurfaceVariant,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.5,
                            ),
                          ),
                          Text(
                            assignment.displayTitle,
                            style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 32),
            Text(
              'REPORT DETAILS',
              style: theme.textTheme.labelSmall?.copyWith(
                color: AppTheme.onSurfaceVariant,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _reportType,
              decoration: const InputDecoration(
                labelText: 'Category',
                fillColor: AppTheme.surfaceContainerLowest,
              ),
              items: _reportTypes.entries.map((e) {
                return DropdownMenuItem(
                  value: e.key,
                  child: Row(
                    children: [
                      Icon(e.value['icon'] as IconData, size: 20, color: e.value['color'] as Color),
                      const SizedBox(width: 12),
                      Text(e.value['label'] as String),
                    ],
                  ),
                );
              }).toList(),
              onChanged: (v) => setState(() => _reportType = v ?? 'incident'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _titleController,
              decoration: const InputDecoration(
                labelText: 'Subject / Title',
                fillColor: AppTheme.surfaceContainerLowest,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _bodyController,
              decoration: const InputDecoration(
                labelText: 'Observations & Details',
                alignLabelWithHint: true,
                fillColor: AppTheme.surfaceContainerLowest,
              ),
              maxLines: 8,
            ),
            const SizedBox(height: 24),
            Container(
              decoration: BoxDecoration(
                color: AppTheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(16),
              ),
              child: SwitchListTile(
                title: Text(
                  'Visible to Client Portal',
                  style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                ),
                subtitle: const Text('Should the property manager see this report?'),
                value: _visibleToClient,
                onChanged: (v) => setState(() => _visibleToClient = v),
                activeColor: AppTheme.secondary,
              ),
            ),
            const SizedBox(height: 40),
            FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text('SUBMIT FINAL REPORT'),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
