import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:video_player/video_player.dart';

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
        if (event.resolvedSubsystemName != null &&
            event.resolvedSubsystemName!.isNotEmpty)
          _DetailRow(label: 'Area', value: event.resolvedSubsystemName!),
        if (event.performedBy != null && event.performedBy!.isNotEmpty)
          _DetailRow(label: 'User', value: event.performedBy!),
        _DetailRow(label: 'Event Type', value: event.displayTitle),
        if (event.resolvedZoneName != null &&
            event.resolvedZoneName!.isNotEmpty)
          _DetailRow(
            label: 'Zone',
            value:
                '${event.resolvedZoneName!} ${event.resolvedZoneNumber != null ? '(Z${event.resolvedZoneNumber})' : ''}',
          ),

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
                const Icon(
                  Icons.info_outline_rounded,
                  size: 14,
                  color: AppTheme.onSurfaceVariant,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'No footage links found for this event.',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      color: AppTheme.onSurfaceVariant,
                    ),
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
                  separatorBuilder: (context, index) =>
                      const SizedBox(width: 8),
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
  const _PictureTile({required this.url, required this.type});
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
            _InAppVideoPlayer(url: widget.url)
          else
            _buildImagePlayer(),
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
            final attachAuth =
                token != null && shouldAttachApiAuthHeader(widget.url);
            return Image.network(
              transformUrl(widget.url),
              headers: attachAuth ? {'Authorization': 'Bearer $token'} : null,
              fit: BoxFit.cover,
              cacheWidth: 360, // Limit memory usage for thumbnails
              errorBuilder: (context, error, stackTrace) =>
                  const _EmptyFrame(isVideo: false, isError: true),
              loadingBuilder: (context, child, loadingProgress) {
                if (loadingProgress == null) return child;
                return const _EmptyFrame(isVideo: false);
              },
            );
          },
          loading: () => const _EmptyFrame(isVideo: false),
          error: (error, stackTrace) =>
              const _EmptyFrame(isVideo: false, isError: true),
        );
      },
    );
  }
}

class _InAppVideoPlayer extends ConsumerStatefulWidget {
  const _InAppVideoPlayer({required this.url});
  final String url;

  @override
  ConsumerState<_InAppVideoPlayer> createState() => _InAppVideoPlayerState();
}

class _InAppVideoPlayerState extends ConsumerState<_InAppVideoPlayer> {
  VideoPlayerController? _controller;
  bool _isInitialized = false;
  bool _isDisposed = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    try {
      final token = await ref.read(accessTokenProvider.future);
      if (_isDisposed || !mounted) return;

      final headers = <String, String>{'User-Agent': 'SecureHubMobile/1.0'};

      if (token != null && shouldAttachApiAuthHeader(widget.url)) {
        headers['Authorization'] = 'Bearer $token';
      }

      final transformed = transformUrl(widget.url);
      if (kDebugMode) {
        debugPrint(
          'Initializing video: $transformed with headers: ${headers.keys}',
        );
      }

      _controller = VideoPlayerController.networkUrl(
        Uri.parse(transformed),
        httpHeaders: headers,
      );

      await _controller!.initialize();

      if (_isDisposed || !mounted) {
        await _controller?.dispose();
        _controller = null;
        return;
      }

      setState(() {
        _isInitialized = true;
      });

      _controller!.setVolume(0); // Mute by default
      _controller!.setLooping(true);
      _controller!.play();
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Video initialization error: $e');
      }
      if (!_isDisposed && mounted) {
        setState(() {
          _error = 'Playback failed';
        });
      }
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    _controller?.pause();
    _controller?.dispose();
    _controller = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Container(
        color: Colors.black87,
        alignment: Alignment.center,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              color: Colors.white54,
              size: 32,
            ),
            const SizedBox(height: 8),
            Text(
              _error!,
              style: GoogleFonts.inter(fontSize: 10, color: Colors.white54),
            ),
          ],
        ),
      );
    }

    if (!_isInitialized || _controller == null) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    }

    return GestureDetector(
      onTap: () {
        if (_controller == null || !_controller!.value.isInitialized) return;

        if (_controller!.value.isPlaying) {
          _controller!.pause();
        } else {
          _controller!.play();
        }
        if (mounted) setState(() {});
      },
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox.expand(
            child: FittedBox(
              fit: BoxFit.cover,
              clipBehavior: Clip.hardEdge,
              child: SizedBox(
                width: _controller!.value.size.width,
                height: _controller!.value.size.height,
                child: VideoPlayer(_controller!),
              ),
            ),
          ),
          if (!_controller!.value.isPlaying)
            Container(
              decoration: const BoxDecoration(
                color: Colors.black26,
                shape: BoxShape.circle,
              ),
              padding: const EdgeInsets.all(12),
              child: const Icon(
                Icons.play_arrow_rounded,
                color: Colors.white,
                size: 32,
              ),
            ),
          Positioned(
            bottom: 8,
            right: 8,
            child: IconButton(
              icon: Icon(
                _controller!.value.volume == 0
                    ? Icons.volume_off_rounded
                    : Icons.volume_up_rounded,
                color: Colors.white,
                size: 16,
              ),
              onPressed: () {
                if (_controller == null) return;
                _controller!.setVolume(_controller!.value.volume == 0 ? 1 : 0);
                if (mounted) setState(() {});
              },
              style: IconButton.styleFrom(backgroundColor: Colors.black45),
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
