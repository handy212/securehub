import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:uuid/uuid.dart';

import '../data/guard_api.dart';
import '../models/guard_models.dart';
import '../providers/guard_ops_provider.dart';
import '../utils/checkpoint_qr.dart';

class GuardPatrolScanScreen extends ConsumerStatefulWidget {
  const GuardPatrolScanScreen({super.key, this.assignmentId});

  final String? assignmentId;

  @override
  ConsumerState<GuardPatrolScanScreen> createState() => _GuardPatrolScanScreenState();
}

class _GuardPatrolScanScreenState extends ConsumerState<GuardPatrolScanScreen> {
  final _scannerController = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
    facing: CameraFacing.back,
  );
  bool _processing = false;
  String? _lastCode;

  @override
  void dispose() {
    _scannerController.dispose();
    super.dispose();
  }

  Future<void> _handleScan(String raw) async {
    if (_processing || raw == _lastCode) return;
    _lastCode = raw;
    setState(() => _processing = true);

    final reference = parseCheckpointQr(raw);
    if (!reference.isValid) {
      _showMessage('Unrecognized checkpoint QR code');
      setState(() => _processing = false);
      return;
    }

    final rounds = await ref.read(guardPatrolRoundsProvider.future);
    final filtered = widget.assignmentId == null
        ? rounds
        : rounds.where((r) => r.assignmentId == widget.assignmentId).toList();
    final match = matchCheckpointInRounds(filtered, reference);

    if (match == null) {
      _showMessage('Checkpoint not on your current patrol rounds');
      setState(() => _processing = false);
      return;
    }

    final checkpoint = match.checkpoint;
    final round = match.round;
    if (round.isComplete(checkpoint.id)) {
      _showMessage('${checkpoint.name} already scanned');
      setState(() => _processing = false);
      return;
    }

    try {
      final pos = await readGuardPosition();
      final result = await ref.read(guardApiProvider).scanCheckpoint(
            patrolRoundId: round.id,
            checkpointId: checkpoint.id,
            clientScanId: const Uuid().v4(),
            latitude: pos?.latitude,
            longitude: pos?.longitude,
            withinGeofence: pos != null,
          );
      ref.invalidate(guardPatrolRoundsProvider);
      if (!mounted) return;
      _showMessage(
        result.queued ? 'Scan queued offline' : 'Scanned ${checkpoint.name}',
      );
      if (result.postOrders.isNotEmpty || result.checkpointInstructions.isNotEmpty) {
        await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: Text(checkpoint.name),
            content: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (result.checkpointInstructions.isNotEmpty)
                    Text(result.checkpointInstructions),
                  ...result.postOrders.map(
                    (o) => Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(o.title, style: Theme.of(ctx).textTheme.titleSmall),
                          Text(o.body),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
            ],
          ),
        );
      }
    } catch (e) {
      _showMessage('Scan failed: $e');
    } finally {
      if (mounted) {
        setState(() {
          _processing = false;
          _lastCode = null;
        });
      }
    }
  }

  void _showMessage(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan checkpoint QR')),
      body: Stack(
        fit: StackFit.expand,
        children: [
          MobileScanner(
            controller: _scannerController,
            onDetect: (capture) {
              final barcodes = capture.barcodes;
              for (final barcode in barcodes) {
                final value = barcode.rawValue;
                if (value != null && value.isNotEmpty) {
                  _handleScan(value);
                  break;
                }
              }
            },
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              width: double.infinity,
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.65),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                _processing
                    ? 'Processing scan…'
                    : 'Point at the checkpoint QR label from the admin console.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
