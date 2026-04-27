import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:video_player/video_player.dart';

import '../../../core/api/api_client.dart';
import '../../../core/models/alarm_event.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../../sites/providers/sites_provider.dart';
import '../providers/alarm_control_provider.dart';
import '../providers/event_list_provider.dart';

class AlarmAlertScreen extends ConsumerStatefulWidget {
  const AlarmAlertScreen({super.key, required this.siteId, this.eventId});

  final String siteId;
  final String? eventId;

  @override
  ConsumerState<AlarmAlertScreen> createState() => _AlarmAlertScreenState();
}

class _AlarmAlertScreenState extends ConsumerState<AlarmAlertScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

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
    const supportNumber = '030 824 9444';
    final url = Uri.parse('tel:${supportNumber.replaceAll(' ', '')}');
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  Future<void> _handleDisarm() async {
    HapticFeedback.heavyImpact();

    final poll = ref.read(sitePollProvider(widget.siteId)).valueOrNull;
    var subsystemIds = poll?.subsystems.map((s) => s.id).toList();

    if (subsystemIds == null || subsystemIds.isEmpty) {
      final site = await ref.read(siteDetailProvider(widget.siteId).future);
      subsystemIds = site.subsystems.map((s) => s.id).toList();
    }

    if (subsystemIds.isEmpty) return;

    await ref
        .read(alarmControlNotifierProvider.notifier)
        .sendBulkCommand(
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

    final poll = ref.read(sitePollProvider(widget.siteId)).valueOrNull;
    var subsystemIds = poll?.subsystems.map((s) => s.id).toList();

    if (subsystemIds == null || subsystemIds.isEmpty) {
      final site = await ref.read(siteDetailProvider(widget.siteId).future);
      subsystemIds = site.subsystems.map((s) => s.id).toList();
    }

    if (subsystemIds.isEmpty) return;

    await ref
        .read(alarmControlNotifierProvider.notifier)
        .sendBulkCommand(
          siteId: widget.siteId,
          subsystemIds: subsystemIds,
          action: 'silence',
        );
  }

  @override
  Widget build(BuildContext context) {
    final siteAsync = ref.watch(siteDetailProvider(widget.siteId));
    final eventsAsync = ref.watch(eventListNotifierProvider(widget.siteId));

    final alarmEvent = widget.eventId != null
        ? eventsAsync.valueOrNull?.firstWhere(
            (e) => e.id == widget.eventId,
            orElse: () =>
                eventsAsync.valueOrNull?.firstOrNull ?? const AlarmEvent(),
          )
        : eventsAsync.valueOrNull?.firstWhere(
            (e) => e.eventCategory == 'alarm',
            orElse: () =>
                eventsAsync.valueOrNull?.firstOrNull ?? const AlarmEvent(),
          );

    final site = siteAsync.valueOrNull;
    final channels =
        site?.videoDevices.expand((device) => device.channels).toList() ?? [];
    final firstOnlineChannel = channels
        .where((channel) => channel.isOnline)
        .firstOrNull;
    final headline = alarmEvent?.alertHeadline ?? 'Alarm Triggered';

    return Scaffold(
      backgroundColor: AppTheme.alarmOverlayBg,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: const BoxDecoration(
                      color: AppTheme.alarmRed,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.security_rounded,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'SecureHub',
                    style: GoogleFonts.inter(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.alarmRed,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    'System Live',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.alarmRed.withValues(alpha: 0.6),
                    ),
                  ),
                ],
              ),
            ),
            const Spacer(),
            ScaleTransition(
              scale: _pulseAnimation,
              child: Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  color: AppTheme.alarmRed,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.alarmRed.withValues(alpha: 0.4),
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
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                children: [
                  Text(
                    alarmEvent != null && headline.isNotEmpty
                        ? 'ALARM TRIGGERED: ${headline.toUpperCase()}'
                        : 'ALARM TRIGGERED',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.alarmRed,
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
                      color: AppTheme.alarmRed.withValues(alpha: 0.8),
                      letterSpacing: 2,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 48),
            Expanded(
              child: Center(
                child: eventsAsync.when(
                  loading: () => const CircularProgressIndicator(),
                  error: (err, _) =>
                      const _AlertFallback(message: 'COULD NOT LOAD EVENT'),
                  data: (_) => alarmEvent != null
                      ? _MediaPreview(
                          siteId: widget.siteId,
                          event: alarmEvent,
                          fallbackChannel: firstOnlineChannel,
                        )
                      : const _AlertFallback(message: 'NO ACTIVE ALARM FOUND'),
                ),
              ),
            ),
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
                        backgroundColor: AppTheme.alarmRed,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        elevation: 8,
                        shadowColor: AppTheme.alarmRed.withValues(alpha: 0.4),
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
                      color: AppTheme.alarmRed.withValues(alpha: 0.5),
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

class _AlertFallback extends StatelessWidget {
  const _AlertFallback({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(
          Icons.videocam_off_rounded,
          color: AppTheme.alarmRed.withValues(alpha: 0.2),
          size: 48,
        ),
        const SizedBox(height: 12),
        Text(
          message,
          style: GoogleFonts.inter(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: AppTheme.alarmRed.withValues(alpha: 0.4),
          ),
        ),
      ],
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
          error: (err, _) => const _AlertFallback(message: 'MEDIA ERROR'),
          data: (pics) {
            if (pics.isNotEmpty) {
              final media = pics.firstWhere(
                (pic) => pic.type == 'video',
                orElse: () => pics.first,
              );
              final evidenceLabel =
                  'EVIDENCE • ${(event.resolvedZoneName ?? event.displayTitle).toUpperCase()}';
              return Stack(
                children: [
                  Positioned.fill(
                    child: media.type == 'video'
                        ? _AlertVideoView(url: media.url)
                        : _PictureView(url: media.url),
                  ),
                  _buildBadge(evidenceLabel, isLive: false),
                ],
              );
            }

            if (fallbackChannel != null) {
              final liveLabel =
                  'LIVE • ${(event.resolvedZoneName ?? fallbackChannel!.name).toUpperCase()}';
              return Stack(
                children: [
                  Positioned.fill(
                    child: _LiveStreamView(
                      siteId: siteId,
                      channel: fallbackChannel!,
                    ),
                  ),
                  _buildBadge(liveLabel, isLive: true),
                  const Positioned(
                    bottom: 16,
                    right: 16,
                    child: _VerifyingBadge(),
                  ),
                ],
              );
            }

            return const _AlertFallback(message: 'NO MEDIA AVAILABLE');
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
          color: AppTheme.alarmRed,
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
}

class _AlertVideoView extends ConsumerStatefulWidget {
  const _AlertVideoView({required this.url});
  final String url;

  @override
  ConsumerState<_AlertVideoView> createState() => _AlertVideoViewState();
}

class _AlertVideoViewState extends ConsumerState<_AlertVideoView> {
  VideoPlayerController? _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    try {
      final token = await ref.read(accessTokenProvider.future);
      if (!mounted) return;

      final headers = <String, String>{'User-Agent': 'SecureHubMobile/1.0'};
      if (token != null && shouldAttachApiAuthHeader(widget.url)) {
        headers['Authorization'] = 'Bearer $token';
      }

      final controller = VideoPlayerController.networkUrl(
        Uri.parse(transformUrl(widget.url)),
        httpHeaders: headers,
      );
      await controller.initialize();

      if (!mounted) {
        await controller.dispose();
        return;
      }

      await controller.setVolume(0);
      await controller.setLooping(true);
      await controller.play();

      setState(() {
        _controller = controller;
      });
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Alarm alert video error: $e');
      }
      if (mounted) {
        setState(() => _error = 'VIDEO UNAVAILABLE');
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    if (_error != null) {
      return const _AlertFallback(message: 'VIDEO UNAVAILABLE');
    }
    if (controller == null || !controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        FittedBox(
          fit: BoxFit.cover,
          clipBehavior: Clip.hardEdge,
          child: SizedBox(
            width: controller.value.size.width,
            height: controller.value.size.height,
            child: VideoPlayer(controller),
          ),
        ),
        Positioned(
          bottom: 12,
          right: 12,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.55),
              borderRadius: BorderRadius.circular(100),
            ),
            child: IconButton(
              visualDensity: VisualDensity.compact,
              icon: Icon(
                controller.value.volume == 0
                    ? Icons.volume_off_rounded
                    : Icons.volume_up_rounded,
                color: Colors.white,
              ),
              onPressed: () {
                controller.setVolume(controller.value.volume == 0 ? 1 : 0);
                if (mounted) {
                  setState(() {});
                }
              },
            ),
          ),
        ),
      ],
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
      data: (token) {
        final attachAuth = token != null && shouldAttachApiAuthHeader(url);
        return Image.network(
          transformUrl(url),
          headers: attachAuth ? {'Authorization': 'Bearer $token'} : null,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) => const Center(
            child: Icon(
              Icons.broken_image_rounded,
              size: 48,
              color: Colors.grey,
            ),
          ),
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return const Center(child: CircularProgressIndicator());
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stackTrace) => const Center(
        child: Icon(Icons.error_rounded, size: 48, color: Colors.red),
      ),
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
        data: (token) {
          final attachAuth = token != null && shouldAttachApiAuthHeader(url);
          return Image.network(
            transformUrl(url),
            headers: attachAuth ? {'Authorization': 'Bearer $token'} : null,
            fit: BoxFit.cover,
            gaplessPlayback: true,
            errorBuilder: (context, error, stackTrace) => const Center(
              child: Icon(
                Icons.videocam_off_rounded,
                size: 48,
                color: Colors.grey,
              ),
            ),
            loadingBuilder: (context, child, loadingProgress) {
              if (loadingProgress == null) return child;
              return const Center(child: CircularProgressIndicator());
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stackTrace) => const Center(
          child: Icon(Icons.error_rounded, size: 48, color: Colors.red),
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stackTrace) => const Center(
        child: Icon(Icons.error_rounded, size: 48, color: Colors.red),
      ),
    );
  }
}

class _VerifyingBadge extends StatelessWidget {
  const _VerifyingBadge();

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
          backgroundColor: isPrimary
              ? AppTheme.primary
              : AppTheme.surfaceContainerLowest,
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
