import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/sites_provider.dart';
import '../../../core/api/api_client.dart';

class CameraLiveScreen extends ConsumerWidget {
  const CameraLiveScreen({
    super.key,
    required this.siteId,
    required this.channelId,
    required this.channelName,
  });

  final String siteId;
  final String channelId;
  final String channelName;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final streamAsync = ref.watch(cameraLiveUrlProvider(siteId, channelId));

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // ── Video Player / Stream ───────────────────────────────────────────
          Center(
            child: streamAsync.when(
              data: (url) => AspectRatio(
                aspectRatio: 16 / 9,
                child: ref
                    .watch(accessTokenProvider)
                    .when(
                      data: (token) => Image.network(
                        transformUrl(url),
                        headers: token != null
                            ? {'Authorization': 'Bearer $token'}
                            : null,
                        fit: BoxFit.contain,
                        gaplessPlayback: true,
                        loadingBuilder: (context, child, loadingProgress) {
                          if (loadingProgress == null) return child;
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        },
                        errorBuilder: (context, error, stackTrace) =>
                            const _ErrorIndicator(
                              message: 'UNABLE TO LOAD STREAM',
                            ),
                      ),
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (err, _) =>
                          const _ErrorIndicator(message: 'AUTH ERROR'),
                    ),
              ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 40),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.warning_amber_rounded,
                        color: AppTheme.error,
                        size: 48,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'STREAM ERROR',
                        style: GoogleFonts.inter(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        err.toString(),
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          color: Colors.white54,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // ── Header Overlay ──────────────────────────────────────────────────
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.fromLTRB(16, 50, 16, 20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.black.withValues(alpha: 0.8),
                    Colors.transparent,
                  ],
                ),
              ),
              child: Row(
                children: [
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(
                      Icons.arrow_back_ios_new_rounded,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          channelName.toUpperCase(),
                          style: GoogleFonts.inter(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                color: AppTheme.error,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'LIVE MONITORING',
                              style: GoogleFonts.inter(
                                color: Colors.white70,
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),

          // ── Footer Overlay ──────────────────────────────────────────────────
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.fromLTRB(24, 40, 24, 50),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [
                    Colors.black.withValues(alpha: 0.8),
                    Colors.transparent,
                  ],
                ),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _ControlIcon(icon: Icons.mic_off_rounded, label: 'LISTEN'),
                  SizedBox(width: 40),
                  _ControlIcon(
                    icon: Icons.photo_camera_rounded,
                    label: 'SNAPSHOT',
                  ),
                  SizedBox(width: 40),
                  _ControlIcon(
                    icon: Icons.videocam_rounded,
                    label: 'RECORD',
                    color: AppTheme.error,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ControlIcon extends StatelessWidget {
  const _ControlIcon({
    required this.icon,
    required this.label,
    this.color = Colors.white,
  });
  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: color, size: 24),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: GoogleFonts.inter(
            color: Colors.white54,
            fontSize: 9,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.0,
          ),
        ),
      ],
    );
  }
}

class _ErrorIndicator extends StatelessWidget {
  const _ErrorIndicator({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.videocam_off_rounded, color: Colors.white24, size: 48),
        const SizedBox(height: 16),
        Text(
          message,
          style: GoogleFonts.inter(
            color: Colors.white24,
            fontSize: 12,
            fontWeight: FontWeight.w900,
            letterSpacing: 2.0,
          ),
        ),
      ],
    );
  }
}
