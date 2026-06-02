import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/models/alarm_event.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/event_list_provider.dart';
import '../widgets/event_details_inline.dart';

class EventListScreen extends ConsumerStatefulWidget {
  const EventListScreen({super.key, required this.siteId});
  final String siteId;

  @override
  ConsumerState<EventListScreen> createState() => _EventListScreenState();
}

class _EventListScreenState extends ConsumerState<EventListScreen> {
  final _scrollCtrl = ScrollController();
  String? _expandedEventId;

  @override
  void initState() {
    super.initState();
    _scrollCtrl.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollCtrl.dispose();
    super.dispose();
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

  void _onScroll() {
    if (_scrollCtrl.position.pixels >=
        _scrollCtrl.position.maxScrollExtent - 200) {
      ref
          .read(eventListNotifierProvider(widget.siteId).notifier)
          .loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final eventsAsync = ref.watch(eventListNotifierProvider(widget.siteId));

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: CustomScrollView(
        controller: _scrollCtrl,
        slivers: [
          // ── App Bar ──────────────────────────────────────────────────────
          SliverAppBar(
            pinned: true,
            backgroundColor: Colors.transparent,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            scrolledUnderElevation: 0,
            automaticallyImplyLeading: false,
            expandedHeight: 120,
            flexibleSpace: FlexibleSpaceBar(
              titlePadding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
              title: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Security Log',
                      style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.primary,
                          letterSpacing: -0.5)),
                  Text('Chronological audit of all activity',
                      style: TextStyle(
                          fontSize: 12, color: AppTheme.onSurfaceVariant)),
                ],
              ),
            ),
          ),

          // ── Events ────────────────────────────────────────────────────────
          eventsAsync.when(
            loading: () => const SliverFillRemaining(
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (err, _) => SliverFillRemaining(
              child: _ErrorBody(
                message: err.toString(),
                onRetry: () => ref
                    .read(eventListNotifierProvider(widget.siteId).notifier)
                    .refresh(),
              ),
            ),
            data: (events) {
              if (events.isEmpty) {
                return SliverFillRemaining(
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(28),
                          decoration: BoxDecoration(
                            color: AppTheme.secondaryContainer.withValues(alpha: 0.3),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.history_toggle_off_rounded,
                              size: 40, color: AppTheme.secondary),
                        ),
                        const SizedBox(height: 24),
                        Text('No activity recorded',
                            style: TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 18,
                                color: AppTheme.primary)),
                      ],
                    ),
                  ),
                );
              }

              final grouped = _groupEvents(events);

              return SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                        (context, index) {
                      final date = grouped.keys.elementAt(index);
                      final dateEvents = grouped[date]!;
                      return _EventGroup(
                        date: date,
                        events: dateEvents,
                        siteId: widget.siteId,
                        expandedEventId: _expandedEventId,
                        onToggleExpand: _onToggleExpand,
                      );
                    },
                    childCount: grouped.length,
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Map<String, List<AlarmEvent>> _groupEvents(List<AlarmEvent> events) {
    final Map<String, List<AlarmEvent>> grouped = {};
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final yesterday = today.subtract(const Duration(days: 1));

    for (final event in events) {
      final dt =
          DateTime.tryParse(event.occurredAt)?.toLocal() ?? DateTime.now();
      final dateOnly = DateTime(dt.year, dt.month, dt.day);

      String key;
      if (dateOnly == today) {
        key = 'Today';
      } else if (dateOnly == yesterday) {
        key = 'Yesterday';
      } else {
        key = DateFormat('EEEE, d MMMM').format(dateOnly);
      }

      grouped.putIfAbsent(key, () => []).add(event);
    }
    return grouped;
  }
}

class _EventGroup extends StatelessWidget {
  const _EventGroup({
    required this.date,
    required this.events,
    required this.siteId,
    required this.expandedEventId,
    required this.onToggleExpand,
  });

  final String date;
  final List<AlarmEvent> events;
  final String siteId;
  final String? expandedEventId;
  final ValueChanged<String> onToggleExpand;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 12, top: 12),
          child: Text(
            date.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
              color: AppTheme.onSurfaceVariant,
            ),
          ),
        ),
        ...events.map((e) => _EventTile(
              event: e,
              siteId: siteId,
              isExpanded: expandedEventId == e.id,
              onToggle: () => onToggleExpand(e.id),
            )),
        const SizedBox(height: 16),
      ],
    );
  }
}

class _EventTile extends StatelessWidget {
  const _EventTile({
    required this.event,
    required this.siteId,
    required this.isExpanded,
    required this.onToggle,
  });

  final AlarmEvent event;
  final String siteId;
  final bool isExpanded;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final color = _severityColor(event);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onToggle,
              borderRadius: BorderRadius.circular(16),
              child: Row(
                children: [
                  // 4px tonal bar
                  Container(
                    width: 4,
                    height: 72,
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: const BorderRadius.horizontal(
                          left: Radius.circular(16)),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.08),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(_iconForEvent(event), color: color, size: 20),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(event.displayTitle.toUpperCase(),
                            style: TextStyle(
                                fontWeight: FontWeight.w900,
                                fontSize: 13,
                                letterSpacing: 0.2,
                                color: AppTheme.primary)),
                        if (!isExpanded) ...[
                          const SizedBox(height: 2),
                          Text(
                            event.displaySubtitle,
                            style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.onSurfaceVariant),
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
                            child: Icon(Icons.videocam_rounded,
                                size: 16, color: AppTheme.secondary),
                          ),
                        Icon(
                          isExpanded
                              ? Icons.expand_less_rounded
                              : Icons.expand_more_rounded,
                          color:
                              AppTheme.onSurfaceVariant.withValues(alpha: 0.5),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
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

  IconData _iconForEvent(AlarmEvent event) {
    final type = event.normalizedEventType.toLowerCase();
    if (event.eventCategory == 'alarm') return Icons.gpp_maybe_rounded;
    if (type.contains('armaway') || type.contains('arm')) return Icons.shield_rounded;
    if (type.contains('stayarm') || type.contains('stay')) return Icons.home_rounded;
    if (type.contains('disarm')) return Icons.lock_open_rounded;
    if (type.contains('battery')) return Icons.battery_alert_rounded;
    if (type.contains('silence')) return Icons.volume_off_rounded;
    return Icons.history_rounded;
  }

  Color _severityColor(AlarmEvent event) {
    final type = event.normalizedEventType.toLowerCase();
    
    // Red strictly for active Alarms and Tampers
    if (event.eventCategory == 'alarm' || type.contains('tamper')) {
      return AppTheme.error;
    }
    
    // Slate for Armed states (Away/Stay)
    if (type.contains('armaway') || type.contains('arm') || type.contains('stayarm') || type.contains('stay')) {
      return AppTheme.primary;
    }
    
    // Green for Disarmed, Restored, and Secure states
    if (type.contains('disarm') || type.contains('restore') || type.contains('secure')) {
      return AppTheme.secondary;
    }
    
    // Fallback/Neutral
    return AppTheme.onSurfaceVariant;
  }
}

class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_rounded,
                size: 48, color: AppTheme.onSurfaceVariant),
            const SizedBox(height: 12),
            Text(message,
                textAlign: TextAlign.center,
                style: TextStyle(color: AppTheme.onSurfaceVariant)),
            const SizedBox(height: 16),
            FilledButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}


