import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/models/site.dart';

class CameraPreviewSection extends StatelessWidget {
  const CameraPreviewSection({
    super.key,
    required this.siteId,
    required this.videoDevices,
  });

  final String siteId;
  final List<VideoDevice> videoDevices;

  @override
  Widget build(BuildContext context) {
    if (videoDevices.isEmpty) return const SizedBox.shrink();

    final channels = videoDevices.expand((d) => d.channels).toList();
    if (channels.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 12),
          child: Text(
            'LIVE CAMERAS',
            style: TextStyle(
              fontFamily: AppTheme.fontFamily,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
              color: AppTheme.onSurfaceVariant,
            ),
          ),
        ),
        SizedBox(
          height: 160,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: channels.length,
            separatorBuilder: (_, _) => const SizedBox(width: 12),
            itemBuilder: (context, i) =>
                _CameraCard(siteId: siteId, channel: channels[i]),
          ),
        ),
      ],
    );
  }
}

class _CameraCard extends StatelessWidget {
  const _CameraCard({required this.siteId, required this.channel});

  final String siteId;
  final VideoChannel channel;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: channel.isOnline
          ? () {
              HapticFeedback.lightImpact();
              context.push(
                '/camera/$siteId/${channel.id}/${Uri.encodeComponent(channel.name)}',
              );
            }
          : null,
      child: Container(
        width: 240,
        decoration: BoxDecoration(
          color: AppTheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(20),
          boxShadow: AppTheme.cardShadow,
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(
          children: [
            // Background / Static Placeholder
            Positioned.fill(
              child: Container(
                color: Colors.black,
                child: Opacity(
                  opacity: channel.isOnline ? 0.3 : 0.6,
                  child: Container(
                    color: Colors.grey[900],
                    child: Center(
                      child: Icon(
                        Icons.camera_alt_rounded,
                        color: Colors.white.withValues(alpha: 0.1),
                        size: 48,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            if (!channel.isOnline)
              Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.05),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.videocam_off_rounded,
                        color: Colors.white54,
                        size: 28,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'SIGNAL LOST',
                      style: TextStyle(
                        fontFamily: AppTheme.fontFamily,
                        color: Colors.white.withValues(alpha: 0.4),
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2.0,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'RECONNECTING...',
                      style: TextStyle(
                        fontFamily: AppTheme.fontFamily,
                        color: Colors.white.withValues(alpha: 0.2),
                        fontSize: 8,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ],
                ),
              ),
            Positioned.fill(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withValues(alpha: 0.1),
                      Colors.transparent,
                      Colors.black.withValues(alpha: 0.6),
                    ],
                  ),
                ),
              ),
            ),
            // Status Badge
            Positioned(
              top: 12,
              left: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                decoration: BoxDecoration(
                  color:
                      channel.isOnline ? AppTheme.error : Colors.grey.shade800,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (channel.isOnline)
                      Container(
                        width: 5,
                        height: 5,
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                        ),
                      ),
                    if (channel.isOnline) const SizedBox(width: 4),
                    Text(
                      channel.isOnline ? 'LIVE' : 'OFFLINE',
                      style: TextStyle(
                        fontFamily: AppTheme.fontFamily,
                        fontSize: 8,
                        fontWeight: FontWeight.w900,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Positioned(
              bottom: 12,
              left: 12,
              right: 12,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    channel.name.toUpperCase(),
                    style: TextStyle(
                      fontFamily: AppTheme.fontFamily,
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  if (channel.isOnline)
                    Text(
                      'Tap to open live view',
                      style: TextStyle(
                        fontFamily: AppTheme.fontFamily,
                        color: Colors.white.withValues(alpha: 0.72),
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                ],
              ),
            ),
            if (channel.isOnline)
              Center(
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.2),
                    ),
                  ),
                  child: const Icon(
                    Icons.play_arrow_rounded,
                    color: Colors.white,
                    size: 24,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
