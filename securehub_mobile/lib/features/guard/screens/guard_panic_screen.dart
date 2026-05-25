import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/guard_api.dart';
import '../providers/guard_ops_provider.dart';

class GuardPanicScreen extends ConsumerStatefulWidget {
  const GuardPanicScreen({super.key});

  @override
  ConsumerState<GuardPanicScreen> createState() => _GuardPanicScreenState();
}

class _GuardPanicScreenState extends ConsumerState<GuardPanicScreen> {
  final _noteController = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    setState(() => _sending = true);
    try {
      final pos = await readGuardPosition();
      final assignment = ref.read(guardActiveAssignmentProvider);
      await ref.read(guardApiProvider).raisePanic(
            assignmentId: assignment?.id,
            latitude: pos?.latitude,
            longitude: pos?.longitude,
            note: _noteController.text.trim(),
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('SOS sent to control')),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('SOS failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SOS / Panic')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Hold to confirm you need immediate assistance. Control will be notified with your location.',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _noteController,
              decoration: const InputDecoration(
                labelText: 'Note (optional)',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
            const Spacer(),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: _sending ? null : _send,
              child: _sending
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('SEND SOS'),
            ),
          ],
        ),
      ),
    );
  }
}
