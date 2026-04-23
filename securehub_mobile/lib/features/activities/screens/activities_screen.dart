import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/models/alarm_event.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_surfaces.dart';
import '../../../shared/widgets/shimmer_loading.dart';
import '../../alarms/providers/event_list_provider.dart';
import '../../alarms/widgets/event_details_inline.dart';
import '../../sites/providers/selected_site_provider.dart';

class ActivitiesScreen extends ConsumerStatefulWidget {
  const ActivitiesScreen({super.key});

  @override
  ConsumerState<ActivitiesScreen> createState() => _ActivitiesScreenState();
}

class _ActivitiesScreenState extends ConsumerState<ActivitiesScreen> {
  String _searchQuery = '';
  String _typeFilter = 'all';
  String? _expandedEventId;

  bool _onScrollNotification(ScrollNotification notification, String siteId) {
    if (notification is ScrollEndNotification &&
        notification.metrics.extentAfter < 300) {
      // Use a microtask or scheduleFrame to avoid calling during build if triggered by layout
      Future.microtask(() {
        if (mounted) {
          ref.read(eventListNotifierProvider(siteId).notifier).loadMore();
        }
      });
    }
    return false;
  }

  void _onToggleExpand(String eventId) {
    setState(() {
      if (_expandedEventId == eventId) {
        _expandedEventId = null;
      } else {
        _expandedEventId = eventId;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final siteId = ref.watch(currentSiteIdProvider);
    final eventsAsync =
        siteId == null ? null : ref.watch(eventListNotifierProvider(siteId));

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: NotificationListener<ScrollNotification>(
        onNotification: siteId == null
            ? (_) => false
            : (n) => _onScrollNotification(n, siteId),
        child: CustomScrollView(
            physics: const BouncingScrollPhysics(),
            slivers: [

              // ── Search & Filter ──────────────────────────────────────────────
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                  child: AppPanel(
                    backgroundColor: AppTheme.surfaceContainerLow,
                    padding: const EdgeInsets.fromLTRB(18, 18, 18, 18),
                    child: Column(
                      children: [
                        TextField(
                          onChanged: (v) => setState(() => _searchQuery = v),
                          style: GoogleFonts.inter(
                            color: AppTheme.onSurface,
                            fontSize: 14,
                          ),
                          decoration: InputDecoration(
                            hintText: 'Search by event, user, or zone...',
                            hintStyle: GoogleFonts.inter(
                              color: AppTheme.onSurfaceVariant.withValues(
                                alpha: 0.5,
                              ),
                              fontSize: 14,
                            ),
                            prefixIcon: const Padding(
                              padding: EdgeInsets.only(left: 20, right: 12),
                              child: Icon(
                                Icons.search_rounded,
                                size: 20,
                                color: AppTheme.onSurfaceVariant,
                              ),
                            ),
                            prefixIconConstraints: const BoxConstraints(
                              minWidth: 0,
                            ),
                            fillColor: AppTheme.surfaceContainerHighest,
                          ),
                        ),
                        const SizedBox(height: 12),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            children: [
                              _FilterPill(
                                label: 'All',
                                isSelected: _typeFilter == 'all',
                                onTap: () => setState(() => _typeFilter = 'all'),
                              ),
                              const SizedBox(width: 8),
                              _FilterPill(
                                label: 'Alarms',
                                isSelected: _typeFilter == 'alarm',
                                onTap: () =>
                                    setState(() => _typeFilter = 'alarm'),
                                activeColor: AppTheme.error,
                              ),
                              const SizedBox(width: 8),
                              _FilterPill(
                                label: 'Operations',
                                isSelected: _typeFilter == 'operation',
                                onTap: () =>
                                    setState(() => _typeFilter = 'operation'),
                                activeColor: AppTheme.onTertiaryContainer,
                              ),
                              const SizedBox(width: 8),
                              _FilterPill(
                                label: 'System',
                                isSelected: _typeFilter == 'system',
                                onTap: () =>
                                    setState(() => _typeFilter = 'system'),
                                activeColor: AppTheme.secondary,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              // ── Events list (per site) ────────────────────────────────────────
              if (siteId != null)
                eventsAsync!.when(
                      loading: () => SliverPadding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        sliver: SliverList(
                          delegate: SliverChildBuilderDelegate(
                            (context, index) => const EventCardShimmer(),
                            childCount: 10,
                          ),
                        ),
                      ),
                      error: (err, stack) => SliverFillRemaining(
                        hasScrollBody: false,
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          child: AppErrorState(
                            title: 'Failed to load activity',
                            message: err.toString(),
                            action: FilledButton.icon(
                              onPressed: () => ref.invalidate(
                                eventListNotifierProvider(siteId),
                              ),
                              icon: const Icon(Icons.refresh),
                              label: const Text('Try Again'),
                            ),
                          ),
                        ),
                      ),
                      data: (events) {
                        final filtered = ref.watch(
                          filteredEventsProvider(
                            siteId,
                            query: _searchQuery,
                            filter: _typeFilter,
                          ),
                        );

                        if (filtered.isEmpty) {
                          return SliverFillRemaining(
                            hasScrollBody: false,
                            child: _EmptyTrail(
                              hasQuery:
                                  _searchQuery.isNotEmpty || _typeFilter != 'all',
                            ),
                          );
                        }

                        return SliverPadding(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          sliver: SliverList(
                            delegate: SliverChildBuilderDelegate(
                              (context, i) {
                                if (i >= filtered.length) {
                                  return const Padding(
                                    padding: EdgeInsets.symmetric(vertical: 20),
                                    child: Center(
                                      child: SizedBox(
                                        width: 24,
                                        height: 24,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          valueColor: AlwaysStoppedAnimation(
                                              AppTheme.primary),
                                        ),
                                      ),
                                    ),
                                  );
                                }
                                return _EventCard(
                                  event: filtered[i],
                                  siteId: siteId,
                                  isExpanded:
                                      _expandedEventId == filtered[i].id,
                                  onToggle: () =>
                                      _onToggleExpand(filtered[i].id),
                                );
                              },
                              childCount: filtered.length +
                                  (ref
                                              .watch(eventListNotifierProvider(
                                                      siteId))
                                              .isLoading &&
                                      ref
                                          .read(eventListNotifierProvider(
                                                  siteId)
                                              .notifier)
                                          .hasMore &&
                                      _searchQuery.isEmpty &&
                                      _typeFilter == 'all'
                                      ? 1
                                      : 0),
                            ),
                          ),
                        );
                      },
                    )
              else
                const SliverFillRemaining(
                  hasScrollBody: false,
                  child: Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: AppEmptyState(
                      icon: Icons.history_toggle_off_rounded,
                      title: 'No Active Site',
                    ),
                  ),
                ),
            ],
          ),
        ),
    );
  }
}

class _EmptyTrail extends StatelessWidget {
  const _EmptyTrail({required this.hasQuery});

  final bool hasQuery;

  @override
  Widget build(BuildContext context) {
    return AppEmptyState(
      icon: hasQuery
          ? Icons.filter_alt_off_rounded
          : Icons.verified_user_rounded,
      title: hasQuery ? 'No Matching Activity' : 'All Clear',
      message: hasQuery
          ? 'Try a broader search or switch filters to review more events.'
          : 'No matching activity to display.',
    );
  }
}

class _EventCard extends StatelessWidget {
  const _EventCard({
    required this.event,
    required this.siteId,
    required this.isExpanded,
    required this.onToggle,
  });
  final AlarmEvent event;
  final String siteId;
  final bool isExpanded;
  final VoidCallback onToggle;

  IconData get _icon {
    final type = event.eventType.toLowerCase();
    if (event.eventCategory == 'alarm') {
      return Icons.gpp_maybe_rounded;
    }
    if (type.contains('armaway') || type.contains('arm')) {
      return Icons.shield_rounded;
    }
    if (type.contains('stayarm') || type.contains('stay')) {
      return Icons.home_rounded;
    }
    if (type.contains('disarm')) {
      return Icons.lock_open_rounded;
    }
    if (type.contains('battery')) {
      return Icons.battery_alert_rounded;
    }
    if (type.contains('silence')) {
      return Icons.volume_off_rounded;
    }
    return Icons.history_rounded;
  }

  Color get _color {
    final type = event.eventType.toLowerCase();

    // Red strictly for active Alarms and Tampers
    if (event.eventCategory == 'alarm' || type.contains('tamper')) {
      return AppTheme.error;
    }

    // Slate for Armed states (Away/Stay)
    if (type.contains('armaway') ||
        type.contains('arm') ||
        type.contains('stayarm') ||
        type.contains('stay')) {
      return AppTheme.primary;
    }

    // Green for Disarmed, Restored, and Secure states
    if (type.contains('disarm') ||
        type.contains('restore') ||
        type.contains('secure')) {
      return AppTheme.secondary;
    }

    // Fallback/Neutral
    return AppTheme.onSurfaceVariant;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(20),
        boxShadow: isExpanded ? [] : AppTheme.cardShadow,
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () {
              HapticFeedback.lightImpact();
              onToggle();
            },
            borderRadius: BorderRadius.circular(20),
            child: Row(
              children: [
                // 4px tonal accent bar
                Container(
                  width: 4,
                  height: 72,
                  decoration: BoxDecoration(
                    color: _color,
                    borderRadius: const BorderRadius.horizontal(
                      left: Radius.circular(20),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: _color.withValues(alpha: 0.08),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(_icon, color: _color, size: 20),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        event.displayTitle.toUpperCase(),
                        style: GoogleFonts.inter(
                          fontWeight: FontWeight.w900,
                          fontSize: 13,
                          letterSpacing: 0.2,
                          color: AppTheme.primary,
                        ),
                      ),
                      if (!isExpanded) ...[
                        const SizedBox(height: 2),
                        Text(
                          event.displaySubtitle,
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.onSurfaceVariant,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 16),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (event.hasEffectiveMedia)
                        const Padding(
                          padding: EdgeInsets.only(right: 8),
                          child: Icon(
                            Icons.videocam_rounded,
                            size: 16,
                            color: AppTheme.secondary,
                          ),
                        ),
                      Icon(
                        isExpanded
                            ? Icons.expand_less_rounded
                            : Icons.expand_more_rounded,
                        color: AppTheme.onSurfaceVariant.withValues(alpha: 0.5),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (isExpanded) ...[
            const Divider(height: 1, indent: 16, endIndent: 16),
            Padding(
              padding: const EdgeInsets.all(16),
              child: EventDetailsInline(event: event, siteId: siteId),
            ),
          ],
        ],
      ),
    );
  }
}

class _FilterPill extends StatefulWidget {
  const _FilterPill({
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.activeColor,
  });
  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final Color? activeColor;

  @override
  State<_FilterPill> createState() => _FilterPillState();
}

class _FilterPillState extends State<_FilterPill> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final color = widget.activeColor ?? AppTheme.primary;
    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      onTap: () {
        HapticFeedback.selectionClick();
        widget.onTap();
      },
      child: AnimatedScale(
        scale: _isPressed ? 0.96 : 1.0,
        duration: const Duration(milliseconds: 100),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: widget.isSelected ? color : AppTheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(100),
            boxShadow: widget.isSelected
                ? [
                    BoxShadow(
                      color: color.withValues(alpha: 0.2),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : [],
          ),
          child: Text(
            widget.label,
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: widget.isSelected
                  ? Colors.white
                  : AppTheme.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }
}
