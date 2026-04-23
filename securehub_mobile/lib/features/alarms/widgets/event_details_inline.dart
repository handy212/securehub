import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/models/alarm_event.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/api/api_client.dart';
import '../providers/event_list_provider.dart';

class EventDetailsInline extends ConsumerWidget {
  const EventDetailsInline({
    super.key,
    required this.event,
    required this.siteId,
  });

  final AlarmEvent event;
  final String siteId;

  String _formatDateTime(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      return DateFormat('HH:mm:ss • dd MMM yyyy').format(dt);
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _DetailRow(label: 'Time', value: _formatDateTime(event.occurredAt)),
        _DetailRow(label: 'Source', value: event.siteName),
        if (event.subsystemName != null && event.subsystemName!.isNotEmpty)
          _DetailRow(label: 'Area', value: event.subsystemName!),
        if (event.performedBy != null && event.performedBy!.isNotEmpty)
          _DetailRow(label: 'User', value: event.performedBy!),
        _DetailRow(label: 'Event Type', value: event.displayTitle),
        if (event.zoneName != null && event.zoneName!.isNotEmpty)
          _DetailRow(label: 'Zone', value: '${event.zoneName!} ${event.zoneNumber != null ? '(Z${event.zoneNumber})' : ''}'),

        if (event.hasEffectiveMedia) ...[
          const SizedBox(height: 16),
          Text(
            'MEDIA EVIDENCE',
            style: GoogleFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              color: AppTheme.onSurfaceVariant.withValues(alpha: 0.5),
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 12),
          _MediaSection(event: event, siteId: siteId),
        ],
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
                letterSpacing: 0.5,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppTheme.onSurface,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MediaSection extends ConsumerWidget {
  const _MediaSection({required this.event, required this.siteId});
  final AlarmEvent event;
  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final picturesAsync = ref.watch(alarmPicturesProvider(siteId, event));

    return picturesAsync.when(
      loading: () => const Center(
        child: Padding(
          padding: EdgeInsets.all(20),
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      ),
      error: (err, _) => Text(
        'Media unavailable: $err',
        style: GoogleFonts.inter(fontSize: 11, color: AppTheme.error),
      ),
      data: (pics) {
        if (pics.isEmpty) {
          return Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.surfaceContainerHigh,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline_rounded, size: 14, color: AppTheme.onSurfaceVariant),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'No footage links found for this event.',
                    style: GoogleFonts.inter(fontSize: 11, color: AppTheme.onSurfaceVariant),
                  ),
                ),
              ],
            ),
          );
        }

        final videoPics = pics.where((p) => p.type == 'video').toList();
        final imagePics = pics.where((p) => p.type == 'image').toList();

        return Column(
          children: [
            if (videoPics.isNotEmpty)
              AspectRatio(
                aspectRatio: 16 / 9,
                child: _PictureTile(url: videoPics.first.url, type: 'video'),
              ),
            if (imagePics.isNotEmpty) ...[
              const SizedBox(height: 8),
              SizedBox(
                height: 120,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: imagePics.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) => AspectRatio(
                    aspectRatio: 1,
                    child: _PictureTile(url: imagePics[i].url, type: 'image'),
                  ),
                ),
              ),
            ],
          ],
        );
      },
    );
  }
}

class _PictureTile extends ConsumerStatefulWidget {
  const _PictureTile({
    required this.url,
    required this.type,
  });
  final String url;
  final String type;

  @override
  ConsumerState<_PictureTile> createState() => _PictureTileState();
}

class _PictureTileState extends ConsumerState<_PictureTile> {
  @override
  Widget build(BuildContext context) {
    final isVideo = widget.type == 'video';

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppTheme.outlineVariant.withValues(alpha: 0.1),
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Content Layer
          if (isVideo)
            const _VideoPlaceholder()
          else
            _buildImagePlayer(),

          // Open External Button
          Positioned(
            top: 8,
            right: 8,
            child: IconButton(
              icon: const Icon(Icons.open_in_new_rounded,
                  size: 16, color: Colors.white),
              onPressed: () =>
                  launchUrl(Uri.parse(widget.url), mode: LaunchMode.externalApplication),
              style: IconButton.styleFrom(
                backgroundColor: Colors.black45,
                padding: const EdgeInsets.all(8),
              ),
              constraints: const BoxConstraints(),
              tooltip: 'Open in browser',
            ),
          ),

        ],
      ),
    );
  }

  Widget _buildImagePlayer() {
    return Consumer(
      builder: (context, ref, _) {
        final tokenAsync = ref.watch(accessTokenProvider);
        return tokenAsync.when(
          data: (token) {
            if (token == null && !widget.url.contains('?X-Amz-')) {
              return const _EmptyFrame(isVideo: false);
            }
            return Image.network(
              transformUrl(widget.url),
              headers: widget.url.contains('?X-Amz-')
                  ? {}
                  : {'Authorization': 'Bearer $token'},
              fit: BoxFit.cover,
              cacheWidth: 360, // Limit memory usage for thumbnails
              errorBuilder: (_, __, ___) =>
              const _EmptyFrame(isVideo: false, isError: true),
              loadingBuilder: (context, child, loadingProgress) {
                if (loadingProgress == null) return child;
                return const _EmptyFrame(isVideo: false);
              },
            );
          },
          loading: () => const _EmptyFrame(isVideo: false),
          error: (_, __) => const _EmptyFrame(isVideo: false, isError: true),
        );
      },
    );
  }
}

class _VideoPlaceholder extends StatelessWidget {
  const _VideoPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.black,
      alignment: Alignment.center,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.play_circle_fill_rounded,
              color: Colors.white,
              size: 40,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'VIDEO EVIDENCE',
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Open externally to view the clip.',
            style: GoogleFonts.inter(
              fontSize: 12,
              color: Colors.white70,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyFrame extends StatelessWidget {
  const _EmptyFrame({required this.isVideo, this.isError = false});
  final bool isVideo;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.surfaceContainerHigh,
      alignment: Alignment.center,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            isError
                ? Icons.broken_image_rounded
                : (isVideo ? Icons.videocam_rounded : Icons.image_rounded),
            color: isError ? AppTheme.error : AppTheme.outlineVariant,
            size: 24,
          ),
          if (isError) ...[
            const SizedBox(height: 8),
            Text(
              'Load failed',
              style: GoogleFonts.inter(
                fontSize: 10,
                color: AppTheme.error,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
