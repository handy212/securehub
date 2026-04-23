import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/models/alarm_event.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/api/api_client.dart';
import '../../sites/providers/sites_provider.dart';
import '../providers/alarm_control_provider.dart';
import '../providers/event_list_provider.dart';

class AlarmAlertScreen extends ConsumerStatefulWidget {
  const AlarmAlertScreen({
    super.key,
    required this.siteId,
    this.eventId,
  });

  final String siteId;
  final String? eventId;

  @override
  ConsumerState<AlarmAlertScreen> createState() => _AlarmAlertScreenState();
}

class _AlarmAlertScreenState extends ConsumerState<AlarmAlertScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.95, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _handleEmergencyCall() async {
    const supportNumber = '030 824 9444'; // Primary support number
    final url = Uri.parse('tel:${supportNumber.replaceAll(' ', '')}');
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  Future<void> _handleDisarm() async {
    HapticFeedback.mediumImpact();
    final siteAsync = ref.read(siteDetailProvider(widget.siteId));
    final site = siteAsync.valueOrNull;
    if (site == null) return;

    final subsystemIds = site.subsystems.map((s) => s.id).toList();
    if (subsystemIds.isEmpty) return;

    await ref.read(alarmControlNotifierProvider.notifier).sendBulkCommand(
          siteId: widget.siteId,
          subsystemIds: subsystemIds,
          action: 'disarm',
        );
    
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  Future<void> _handleSilence() async {
    HapticFeedback.mediumImpact();
    final siteAsync = ref.read(siteDetailProvider(widget.siteId));
    final site = siteAsync.valueOrNull;
    if (site == null) return;

    final subsystemIds = site.subsystems.map((s) => s.id).toList();
    if (subsystemIds.isEmpty) return;

    await ref.read(alarmControlNotifierProvider.notifier).sendBulkCommand(
          siteId: widget.siteId,
          subsystemIds: subsystemIds,
          action: 'silence',
        );
  }

  @override
  Widget build(BuildContext context) {
    final siteAsync = ref.watch(siteDetailProvider(widget.siteId));
    final eventsAsync = ref.watch(eventListNotifierProvider(widget.siteId));
    
    // Find the specific event if ID provided, otherwise take the latest alarm
    final alarmEvent = widget.eventId != null
        ? eventsAsync.valueOrNull?.firstWhere(
            (e) => e.id == widget.eventId, 
            orElse: () => eventsAsync.valueOrNull?.firstOrNull ?? const AlarmEvent())
        : eventsAsync.valueOrNull?.firstWhere(
            (e) => e.eventCategory == 'alarm', 
            orElse: () => eventsAsync.valueOrNull?.firstOrNull ?? const AlarmEvent());

    final site = siteAsync.valueOrNull;
    final channels = site?.videoDevices.expand((d) => d.channels).toList() ?? [];
    final firstOnlineChannel = channels.where((c) => c.isOnline).firstOrNull;

    return Scaffold(
      backgroundColor: AppTheme.errorContainer,
      body: SafeArea(
        child: Column(
          children: [
            // ── Top Bar ──────────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: const BoxDecoration(
                      color: AppTheme.error,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.security_rounded, color: Colors.white, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'SecureHub',
                    style: GoogleFonts.inter(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.onErrorContainer,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    'System Live',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.onErrorContainer.withValues(alpha: 0.6),
                    ),
                  ),
                ],
              ),
            ),

            const Spacer(),

            // ── Pulse Icon ───────────────────────────────────────────────────
            ScaleTransition(
              scale: _pulseAnimation,
              child: Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  color: AppTheme.error,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.error.withValues(alpha: 0.4),
                      blurRadius: 40,
                      spreadRadius: 10,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.notifications_active_rounded,
                  color: Colors.white,
                  size: 60,
                ),
              ),
            ),

            const SizedBox(height: 32),

            // ── Alert Typography ─────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                children: [
                  Text(
                    alarmEvent != null && alarmEvent.displayTitle.isNotEmpty
                        ? 'ALARM TRIGGERED: ${alarmEvent.displayTitle.toUpperCase()}'
                        : 'ALARM TRIGGERED',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.onErrorContainer,
                      height: 1.1,
                      letterSpacing: -1,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'IMMEDIATE ACTION REQUIRED',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.onErrorContainer.withValues(alpha: 0.8),
                      letterSpacing: 2,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 48),

            // ── Media/Camera Section ────────────────────────────────────────
            if (alarmEvent != null)
              _MediaPreview(
                siteId: widget.siteId,
                event: alarmEvent,
                fallbackChannel: firstOnlineChannel,
              ),

            const Spacer(),

            // ── Action Buttons ───────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: _AlertActionButton(
                          icon: Icons.volume_off_rounded,
                          label: 'SILENCE',
                          onTap: _handleSilence,
                          isPrimary: false,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _AlertActionButton(
                          icon: Icons.lock_open_rounded,
                          label: 'DISARM',
                          onTap: _handleDisarm,
                          isPrimary: true,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    height: 72,
                    child: FilledButton.icon(
                      onPressed: _handleEmergencyCall,
                      style: FilledButton.styleFrom(
                        backgroundColor: AppTheme.error,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        elevation: 8,
                        shadowColor: AppTheme.error.withValues(alpha: 0.4),
                      ),
                      icon: const Icon(Icons.emergency_share_rounded, size: 28),
                      label: Text(
                        'EMERGENCY CALL',
                        style: GoogleFonts.inter(
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Monitoring center has been notified and is on standby.',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.onErrorContainer.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MediaPreview extends ConsumerWidget {
  const _MediaPreview({
    required this.siteId,
    required this.event,
    this.fallbackChannel,
  });

  final String siteId;
  final AlarmEvent event;
  final VideoChannel? fallbackChannel;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final picturesAsync = ref.watch(alarmPicturesProvider(siteId, event));

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Container(
        width: double.infinity,
        height: 220,
        decoration: BoxDecoration(
          color: AppTheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(24),
          boxShadow: AppTheme.cardShadow,
        ),
        clipBehavior: Clip.antiAlias,
        child: picturesAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => _buildFallback(context, ref, 'MEDIA ERROR'),
          data: (pics) {
            if (pics.isNotEmpty) {
              return Stack(
                children: [
                  Positioned.fill(
                    child: _PictureView(url: pics.first.url),
                  ),
                  _buildBadge(
                    'EVIDENCE • ${event.zoneName?.toUpperCase() ?? 'ALARM'}',
                    isLive: false,
                  ),
                ],
              );
            }
            
            // Fallback to live camera if event has no media
            if (fallbackChannel != null) {
              return Stack(
                children: [
                  Positioned.fill(
                    child: _LiveStreamView(siteId: siteId, channel: fallbackChannel!),
                  ),
                  _buildBadge(
                    'LIVE • ${fallbackChannel!.name.toUpperCase()}',
                    isLive: true,
                  ),
                  Positioned(
                    bottom: 16,
                    right: 16,
                    child: _VerifyingBadge(),
                  ),
                ],
              );
            }

            return _buildFallback(context, ref, 'NO MEDIA AVAILABLE');
          },
        ),
      ),
    );
  }

  Widget _buildBadge(String label, {required bool isLive}) {
    return Positioned(
      top: 16,
      left: 16,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppTheme.error,
          borderRadius: BorderRadius.circular(100),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (isLive) ...[
              Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
            ],
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFallback(BuildContext context, WidgetRef ref, String message) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.videocam_off_rounded, color: AppTheme.onSurfaceVariant.withValues(alpha: 0.2), size: 48),
          const SizedBox(height: 12),
          Text(
            message,
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: AppTheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
          ),
        ],
      ),
    );
  }
}

class _PictureView extends ConsumerWidget {
  const _PictureView({required this.url});
  final String url;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tokenAsync = ref.watch(accessTokenProvider);
    return tokenAsync.when(
      data: (token) => Image.network(
        transformUrl(url),
        headers: url.contains('?X-Amz-') ? {} : {'Authorization': 'Bearer $token'},
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_rounded),
      ),
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const Icon(Icons.error_rounded),
    );
  }
}

class _LiveStreamView extends ConsumerWidget {
  const _LiveStreamView({required this.siteId, required this.channel});
  final String siteId;
  final VideoChannel channel;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final streamAsync = ref.watch(cameraLiveUrlProvider(siteId, channel.id));
    final tokenAsync = ref.watch(accessTokenProvider);

    return streamAsync.when(
      data: (url) => tokenAsync.when(
        data: (token) => Image.network(
          transformUrl(url),
          headers: token != null ? {'Authorization': 'Bearer $token'} : null,
          fit: BoxFit.cover,
          gaplessPlayback: true,
        ),
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const Icon(Icons.error_rounded),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Icon(Icons.error_rounded),
    );
  }
}

class _VerifyingBadge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.primary.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.visibility_rounded, color: Colors.white, size: 14),
          const SizedBox(width: 8),
          Text(
            'Verifying Source...',
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}

class _AlertActionButton extends StatelessWidget {
  const _AlertActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
    required this.isPrimary,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool isPrimary;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 96,
      child: ElevatedButton(
        onPressed: onTap,
        style: ElevatedButton.styleFrom(
          backgroundColor: isPrimary ? AppTheme.primary : AppTheme.surfaceContainerLowest,
          foregroundColor: isPrimary ? Colors.white : AppTheme.primary,
          elevation: 4,
          shadowColor: Colors.black.withValues(alpha: 0.1),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          padding: EdgeInsets.zero,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 32),
            const SizedBox(height: 8),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
