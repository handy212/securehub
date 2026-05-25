import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';

GuardShiftAssignment? _resolveReportAssignment(WidgetRef ref) {
  final active = ref.read(guardActiveAssignmentProvider);
  if (active != null) return active;
  final shifts = ref.read(guardShiftsProvider).valueOrNull;
  if (shifts == null || shifts.isEmpty) return null;
  for (final shift in shifts) {
    if (shift.status == 'clocked_in' || shift.status == 'accepted') {
      return shift;
    }
  }
  return shifts.first;
}

const _reportTypes = <String, String>{
  'incident': 'Incident',
  'daily_activity': 'Daily activity',
  'maintenance': 'Maintenance',
  'visitor': 'Visitor',
  'parking': 'Parking',
  'pass_on': 'Pass-on',
  'other': 'Other',
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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Title is required')),
      );
      return;
    }

    final assignment = _resolveReportAssignment(ref);
    if (assignment == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Accept or clock in to a shift before submitting a report')),
      );
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
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Report submitted')),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Submit failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final assignment = ref.watch(guardActiveAssignmentProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Field report')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (assignment != null)
            Card(
              child: ListTile(
                title: Text(assignment.displayTitle),
                subtitle: Text('Linked to active shift (${assignment.statusLabel})'),
              ),
            )
          else
            const Card(
              child: ListTile(
                title: Text('No clocked-in shift'),
                subtitle: Text('Report will be submitted without shift assignment.'),
              ),
            ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _reportType,
            decoration: const InputDecoration(
              labelText: 'Report type',
              border: OutlineInputBorder(),
            ),
            items: _reportTypes.entries
                .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                .toList(),
            onChanged: (v) => setState(() => _reportType = v ?? 'incident'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _titleController,
            decoration: const InputDecoration(
              labelText: 'Title',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _bodyController,
            decoration: const InputDecoration(
              labelText: 'Details',
              border: OutlineInputBorder(),
            ),
            maxLines: 6,
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            title: const Text('Visible to client'),
            value: _visibleToClient,
            onChanged: (v) => setState(() => _visibleToClient = v),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _submitting ? null : _submit,
            child: _submitting
                ? const SizedBox(
                    height: 22,
                    width: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Submit report'),
          ),
        ],
      ),
    );
  }
}
