import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
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
          const SnackBar(content: Text('SOS Signal Received by Command Center')),
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
    final theme = Theme.of(context);
    
    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: const Text('Emergency SOS'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: AppTheme.errorContainer.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: AppTheme.error.withValues(alpha: 0.1)),
                ),
                child: Column(
                  children: [
                    const Icon(
                      Icons.warning_amber_rounded,
                      color: AppTheme.error,
                      size: 48,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Immediate Assistance Required',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: AppTheme.error,
                        fontWeight: FontWeight.w800,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'This will notify Command Center with your exact GPS location. Only use in real emergencies.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: AppTheme.onErrorContainer,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),
              Text(
                'SITUATION NOTE',
                style: theme.textTheme.labelSmall?.copyWith(
                  color: AppTheme.onSurfaceVariant,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _noteController,
                decoration: const InputDecoration(
                  hintText: 'Describe the situation (e.g. Armed robbery, Medical, Fire)...',
                  fillColor: AppTheme.surfaceContainerLowest,
                ),
                maxLines: 4,
              ),
              const Spacer(),
              _PanicButton(
                onPressed: _send,
                isSending: _sending,
              ),
              const SizedBox(height: 16),
              Text(
                'Hold button to activate SOS',
                style: theme.textTheme.labelSmall?.copyWith(
                  color: AppTheme.onSurfaceVariant,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PanicButton extends StatefulWidget {
  const _PanicButton({required this.onPressed, required this.isSending});
  final VoidCallback onPressed;
  final bool isSending;

  @override
  State<_PanicButton> createState() => _PanicButtonState();
}

class _PanicButtonState extends State<_PanicButton> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _isHolding = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..addStatusListener((status) {
        if (status == AnimationStatus.completed) {
          widget.onPressed();
          _controller.reset();
        }
      });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onLongPressStart: (_) {
        if (!widget.isSending) {
          setState(() => _isHolding = true);
          _controller.forward();
        }
      },
      onLongPressEnd: (_) {
        setState(() => _isHolding = false);
        if (_controller.status != AnimationStatus.completed) {
          _controller.reverse();
        }
      },
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            height: 120,
            width: 120,
            child: CircularProgressIndicator(
              value: _controller.value,
              strokeWidth: 8,
              color: AppTheme.error,
              backgroundColor: AppTheme.error.withValues(alpha: 0.1),
            ),
          ),
          Container(
            height: 100,
            width: 100,
            decoration: BoxDecoration(
              color: widget.isSending ? AppTheme.outline : AppTheme.error,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppTheme.error.withValues(alpha: _isHolding ? 0.4 : 0.2),
                  blurRadius: _isHolding ? 20 : 10,
                  spreadRadius: _isHolding ? 5 : 2,
                )
              ],
            ),
            child: Center(
              child: widget.isSending
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text(
                      'SOS',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1,
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
