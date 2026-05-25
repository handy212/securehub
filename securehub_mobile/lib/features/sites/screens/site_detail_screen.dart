import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:securehub_mobile/core/utils/zone_utils.dart';
import 'package:sliver_tools/sliver_tools.dart';

import '../../../core/api/exceptions.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../../alarms/providers/alarm_control_provider.dart';
import '../../emergency/widgets/emergency_action_card.dart';
import '../providers/sites_provider.dart';
import '../widgets/subsystem_card.dart';
import '../widgets/zone_health_badge.dart';
import '../../../shared/widgets/app_surfaces.dart';
import '../../../shared/widgets/shimmer_loading.dart';

// Split widgets
import '../widgets/site_status_hero.dart';
import '../widgets/bento_action_button.dart';
import '../widgets/camera_preview_section.dart';

class SiteDetailScreen extends ConsumerStatefulWidget {
  const SiteDetailScreen({super.key, required this.siteId});
  final String siteId;

  @override
  ConsumerState<SiteDetailScreen> createState() => _SiteDetailScreenState();
}

class _SiteDetailScreenState extends ConsumerState<SiteDetailScreen> {
  final ScrollController _scrollController = ScrollController();
  final GlobalKey _cameraKey = GlobalKey();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToCameras() {
    final context = _cameraKey.currentContext;
    if (context != null) {
      Scrollable.ensureVisible(
        context,
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.sizeOf(context);
    final isCompactHeight = screenSize.height < 780;
    final isCompactWidth = screenSize.width < 390;
    final horizontalPadding = isCompactWidth ? 16.0 : 20.0;
    final statusCardPadding = isCompactHeight ? 22.0 : 32.0;
    final sectionGap = isCompactHeight ? 10.0 : 16.0;
    final statusTitleSize = isCompactHeight ? 19.0 : 22.0;
    final statusBodySize = isCompactHeight ? 11.0 : 12.0;

    final siteAsync = ref.watch(siteDetailProvider(widget.siteId));
    final pollAsync = ref.watch(sitePollProvider(widget.siteId));
    final cmdState = ref.watch(alarmControlNotifierProvider);

    ref.listen(hardwareRefreshProvider(widget.siteId), (_, next) {
      if (next is AsyncError && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Sync failed — device may be offline.')),
        );
      }
    });

    ref.listen(alarmControlNotifierProvider, (prev, next) {
      if (next is CommandSuccess || next is CommandFailed) {
        Future.delayed(const Duration(seconds: 5), () {
          if (mounted && ref.read(alarmControlNotifierProvider) == next) {
            ref.read(alarmControlNotifierProvider.notifier).reset();
          }
        });
      }
    });

    final siteList = ref.watch(siteListProvider).valueOrNull;
    final siteFromList = siteList
        ?.where((s) => s.id == widget.siteId)
        .firstOrNull;
    final site = siteAsync.valueOrNull ?? siteFromList;
    final poll = pollAsync.valueOrNull;
    final isSuspended =
        (siteAsync is AsyncError && siteAsync.error is SuspensionException) ||
        (pollAsync is AsyncError && pollAsync.error is SuspensionException);

    // Merge logic
    final Map<String, Subsystem> subsystemMap = {};
    if (site != null) {
      for (final s in site.subsystems) {
        subsystemMap[s.id] = s;
      }
      for (final d in site.devices) {
        for (final s in d.subsystems) {
          subsystemMap[s.id] = s;
        }
      }
    }
    if (poll != null) {
      for (final s in poll.subsystems) {
        if (subsystemMap.containsKey(s.id)) {
          subsystemMap[s.id] = subsystemMap[s.id]!.copyWith(status: s.status);
        } else {
          subsystemMap[s.id] = s;
        }
      }
    }
    final allSubsystems = subsystemMap.values.toList();
    final allSubsystemIds = subsystemMap.keys.toList();

    final verifyParam = GoRouterState.of(context).uri.queryParameters['verify'];
    if (verifyParam == 'true') {
      WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToCameras());
    }

    final isArmedAway = allSubsystems.any((s) => s.status == 'armed');
    final isArmedStay = allSubsystems.any((s) => s.status == 'stay');
    final hasAlarm = (poll?.activeAlarmCount ?? 0) > 0;
    final isArmed = isArmedAway || isArmedStay;
    final openZones = allSubsystems
        .expand((subsystem) => subsystem.zones)
        .where((zone) => zone.state.toLowerCase() == 'open')
        .toList();
    final hasOpenZone = openZones.isNotEmpty;
    final openZoneSummary = openZones
        .take(3)
        .map((zone) => zone.name)
        .join(', ');
    final hasMoreOpenZones = openZones.length > 3;
    final statusTitle = hasAlarm
        ? 'Alarm response required'
        : hasOpenZone
        ? 'System not ready'
        : isArmedAway
        ? 'Perimeter fully armed'
        : isArmedStay
        ? 'Stay mode active'
        : 'System ready';
    final statusSubtitle = hasAlarm
        ? 'Review event history and camera verification before issuing further commands.'
        : hasOpenZone
        ? 'Open zone${openZones.length == 1 ? '' : 's'}: $openZoneSummary${hasMoreOpenZones ? ' +${openZones.length - 3} more' : ''}.'
        : (poll?.offlineDeviceCount ?? 0) > 0 ||
              (site?.devices.any((d) => !d.isOnline) ?? false)
        ? 'Some devices are currently offline. Verify device health before relying on site status.'
        : 'All zones are reporting normally.';
    final statusMessageColor = hasAlarm
        ? AppTheme.error
        : hasOpenZone
        ? AppTheme.error
        : ((poll?.offlineDeviceCount ?? 0) > 0 ||
              (site?.devices.any((d) => !d.isOnline) ?? false))
        ? AppTheme.onSurfaceVariant
        : AppTheme.secondary;
    final readinessTone = hasAlarm
        ? AppTheme.error
        : hasOpenZone
        ? AppTheme.error
        : (isArmed ? AppTheme.primary : AppTheme.secondary);
    final cameraCount = (site?.videoDevices ?? const <VideoDevice>[]).fold<int>(
      0,
      (count, device) => count + device.channels.length,
    );

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: CustomScrollView(
        controller: _scrollController,
        physics: const BouncingScrollPhysics(),
        slivers: [
          if (cmdState is CommandSuccess || cmdState is CommandFailed)
            SliverToBoxAdapter(
              child: _CommandBanner(
                message: cmdState is CommandSuccess
                    ? 'Command sent: ${cmdState.command.action.toUpperCase()}'
                    : (cmdState as CommandFailed).message,
                isError:
                    cmdState is CommandFailed ||
                    (cmdState is CommandSuccess &&
                        cmdState.command.status == 'failed'),
                onDismiss: () =>
                    ref.read(alarmControlNotifierProvider.notifier).reset(),
              ),
            ),
          if (isSuspended) const SliverToBoxAdapter(child: _LockdownBanner()),
          SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                isCompactHeight ? 4 : 8,
                horizontalPadding,
                0,
              ),
              child: Column(
                children: [
                  Container(
                    width: double.infinity,
                    padding: EdgeInsets.all(statusCardPadding),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceContainerLowest,
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: AppTheme.cardShadow,
                    ),
                    child: Column(
                      children: [
                        SiteStatusHero(
                          isArmed: isArmed,
                          hasAlarm: hasAlarm,
                          isSuspended: isSuspended,
                          tone: readinessTone,
                          compact: isCompactHeight,
                        ),
                        SizedBox(height: isCompactHeight ? 14 : 20),
                        Text(
                          statusTitle,
                          style: TextStyle(
                            fontFamily: AppTheme.fontFamily,
                            fontSize: statusTitleSize,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.primary,
                          ),
                        ),
                        SizedBox(height: isCompactHeight ? 4 : 6),
                        Text(
                          statusSubtitle,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontFamily: AppTheme.fontFamily,
                            fontSize: statusBodySize,
                            height: 1.5,
                            fontWeight: FontWeight.w600,
                            color: statusMessageColor,
                          ),
                        ),
                      ],
                    ),
                  ),
                  SizedBox(height: sectionGap),
                  if (!isSuspended && site != null) ...[
                    EmergencyActionCard(site: site, triggerContext: 'on_site'),
                    SizedBox(height: isCompactHeight ? 8 : 12),
                  ],
                  if (!isSuspended) ...[
                    Row(
                      children: [
                        Expanded(
                          child: BentoActionButton(
                            icon: Icons.exit_to_app_rounded,
                            label: 'Arm Away',
                            isPrimary: isArmedAway,
                            isActive: isArmedAway,
                            compact: isCompactHeight,
                            onTap: () async {
                              HapticFeedback.lightImpact();
                              if (allSubsystemIds.isNotEmpty) {
                                await _warnAndSendArmCommand(
                                  context,
                                  ref,
                                  siteId: widget.siteId,
                                  subsystemIds: allSubsystemIds,
                                  action: 'arm',
                                  bypassedZoneNames: openZones
                                      .map((zone) => zone.name)
                                      .toList(),
                                );
                              }
                            },
                          ),
                        ),
                        SizedBox(width: isCompactWidth ? 8 : 12),
                        Expanded(
                          child: BentoActionButton(
                            icon: Icons.home_rounded,
                            label: 'Arm Stay',
                            isPrimary: isArmedStay,
                            isActive: isArmedStay,
                            compact: isCompactHeight,
                            onTap: () async {
                              HapticFeedback.lightImpact();
                              if (allSubsystemIds.isNotEmpty) {
                                await _warnAndSendArmCommand(
                                  context,
                                  ref,
                                  siteId: widget.siteId,
                                  subsystemIds: allSubsystemIds,
                                  action: 'stay-arm',
                                  bypassedZoneNames: openZones
                                      .map((zone) => zone.name)
                                      .toList(),
                                );
                              }
                            },
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: isCompactHeight ? 8 : 12),
                    SizedBox(
                      width: double.infinity,
                      child: BentoActionButton(
                        icon: Icons.lock_open_rounded,
                        label: 'Disarm',
                        isPrimary: !isArmed,
                        isActive: !isArmed,
                        isFullWidth: true,
                        compact: isCompactHeight,
                        onTap: () {
                          HapticFeedback.lightImpact();
                          if (allSubsystemIds.isNotEmpty) {
                            _confirmAndSendBulk(
                              context,
                              ref,
                              siteId: widget.siteId,
                              subsystemIds: allSubsystemIds,
                              action: 'disarm',
                            );
                          }
                        },
                      ),
                    ),
                  ],
                  SizedBox(height: isCompactHeight ? 8 : 12),
                  CameraPreviewSection(
                    siteId: widget.siteId,
                    key: _cameraKey,
                    videoDevices: site?.videoDevices ?? [],
                  ),
                  if (cameraCount > 0) ...[
                    SizedBox(height: isCompactHeight ? 8 : 12),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        '$cameraCount camera feed${cameraCount == 1 ? '' : 's'} available',
                        style: TextStyle(
                          fontFamily: AppTheme.fontFamily,
                          fontSize: 12,
                          color: AppTheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ],
                  SizedBox(height: isCompactHeight ? 16 : 24),
                ],
              ),
            ),
          ),
          siteAsync.when(
            loading: () => MultiSliver(
              children: [
                SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(
                      horizontalPadding,
                      0,
                      horizontalPadding,
                      12,
                    ),
                    child: const _AreasSectionHeader(),
                  ),
                ),
                SliverPadding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, index) => const ZoneTileShimmer(),
                      childCount: 3,
                    ),
                  ),
                ),
              ],
            ),
            error: (err, _) => err is SuspensionException
                ? const SliverToBoxAdapter(child: SizedBox.shrink())
                : SliverFillRemaining(
                    child: _ErrorBody(
                      message: err.toString(),
                      onRetry: () =>
                          ref.invalidate(siteDetailProvider(widget.siteId)),
                    ),
                  ),
            data: (site) => MultiSliver(
              children: [
                SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(
                      horizontalPadding,
                      0,
                      horizontalPadding,
                      12,
                    ),
                    child: _AreasSectionHeader(count: allSubsystems.length),
                  ),
                ),
                _SliverSiteBody(
                  allSubsystems: allSubsystems,
                  isSending: cmdState is CommandSending,
                  onAction: (subsystem, action) async {
                    await _confirmAndSend(
                      context,
                      ref,
                      siteId: widget.siteId,
                      subsystem: subsystem,
                      action: action,
                    );
                  },
                ),
                const SliverToBoxAdapter(child: SizedBox(height: 120)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmAndSend(
    BuildContext context,
    WidgetRef ref, {
    required String siteId,
    required Subsystem subsystem,
    required String action,
  }) async {
    final bypassedZoneNames = subsystem.zones
        .where((zone) => zone.state.toLowerCase() == 'open')
        .map((zone) => zone.name)
        .toList();

    await _warnAndSendArmCommand(
      context,
      ref,
      siteId: siteId,
      subsystemIds: [subsystem.id],
      action: action,
      bypassedZoneNames: bypassedZoneNames,
      scopeLabel: subsystem.name,
    );
  }

  Future<void> _warnAndSendArmCommand(
    BuildContext context,
    WidgetRef ref, {
    required String siteId,
    required List<String> subsystemIds,
    required String action,
    required List<String> bypassedZoneNames,
    String? scopeLabel,
  }) async {
    if ((action == 'arm' || action == 'stay-arm') &&
        bypassedZoneNames.isNotEmpty) {
      final shouldContinue = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          backgroundColor: AppTheme.surfaceContainerLowest,
          surfaceTintColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
          ),
          title: const Text(
            'Open Zones',
            style: TextStyle(
              fontWeight: FontWeight.w800,
              color: Colors.red,
            ),
          ),
          content: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 16),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 220),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: bypassedZoneNames
                          .map(
                            (zoneName) => Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Padding(
                                    padding: EdgeInsets.only(top: 2),
                                    child: Icon(
                                      Icons.warning_amber_rounded,
                                      size: 16,
                                      color: AppTheme.error,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      zoneName,
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.primary,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: AppTheme.primary),
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Arm Anyway'),
            ),
          ],
        ),
      );

      if (shouldContinue != true || !context.mounted) {
        return;
      }
    }

    await _confirmAndSendBulk(
      context,
      ref,
      siteId: siteId,
      subsystemIds: subsystemIds,
      action: action,
    );
  }

  Future<void> _confirmAndSendBulk(
    BuildContext context,
    WidgetRef ref, {
    required String siteId,
    required List<String> subsystemIds,
    required String action,
  }) async {
    HapticFeedback.mediumImpact();
    await ref.read(alarmControlNotifierProvider.notifier).sendBulkCommand(
          siteId: siteId,
          subsystemIds: subsystemIds,
          action: action,
        );
  }
}

class _AreasSectionHeader extends StatelessWidget {
  const _AreasSectionHeader({this.count});
  final int? count;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            'Areas',
            style: TextStyle(
              fontFamily: AppTheme.fontFamily,
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.6,
              color: AppTheme.primary,
            ),
          ),
          if (count != null && count! > 0) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                count.toString(),
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                  color: AppTheme.primary,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SliverSiteBody extends StatelessWidget {
  const _SliverSiteBody({
    required this.allSubsystems,
    required this.isSending,
    required this.onAction,
  });
  final List<Subsystem> allSubsystems;
  final bool isSending;
  final Future<void> Function(Subsystem subsystem, String action) onAction;

  @override
  Widget build(BuildContext context) {
    if (allSubsystems.isEmpty) {
      return const SliverToBoxAdapter(
        child: Padding(
          padding: EdgeInsets.all(20),
          child: Text('No subsystems found.'),
        ),
      );
    }

    if (allSubsystems.length == 1) {
      return SliverPadding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
        sliver: SliverToBoxAdapter(
          child: AspectRatio(
            aspectRatio: 2.4,
            child: SubsystemCard(
              subsystem: allSubsystems[0],
              isHero: true,
              onTap: () => _showAreaOptions(context, allSubsystems[0]),
              onArmAway: () => onAction(allSubsystems[0], 'arm'),
              onArmStay: () => onAction(allSubsystems[0], 'stay-arm'),
            ),
          ),
        ),
      );
    }

    return SliverPadding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
      sliver: SliverGrid(
        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
          maxCrossAxisExtent: 220,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          mainAxisExtent: 110,
        ),
        delegate: SliverChildBuilderDelegate(
          (_, i) => SubsystemCard(
            subsystem: allSubsystems[i],
            onTap: () => _showAreaOptions(context, allSubsystems[i]),
          ),
          childCount: allSubsystems.length,
        ),
      ),
    );
  }

  void _showAreaOptions(BuildContext context, Subsystem subsystem) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 40),
        decoration: BoxDecoration(
          color: AppTheme.surfaceContainerLowest,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
          boxShadow: AppTheme.floatingShadow,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 32,
              height: 4,
              margin: const EdgeInsets.only(bottom: 24),
              decoration: BoxDecoration(
                color: AppTheme.outlineVariant.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Text(
              'AREA CONTROL',
              style: TextStyle(
                fontFamily: AppTheme.fontFamily,
                fontSize: 10,
                fontWeight: FontWeight.w900,
                letterSpacing: 2,
                color: AppTheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              subsystem.name,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: AppTheme.primary,
              ),
            ),
            const SizedBox(height: 32),
            _AreaOptionTile(
              icon: Icons.shield_rounded,
              label: 'Arm Away (Area)',
              color: AppTheme.primary,
              onTap: () {
                HapticFeedback.lightImpact();
                Navigator.pop(ctx);
                onAction(subsystem, 'arm');
              },
            ),
            const SizedBox(height: 12),
            _AreaOptionTile(
              icon: Icons.home_rounded,
              label: 'Arm Stay (Area)',
              color: AppTheme.primary,
              onTap: () {
                HapticFeedback.lightImpact();
                Navigator.pop(ctx);
                onAction(subsystem, 'stay-arm');
              },
            ),
            const SizedBox(height: 12),
            _AreaOptionTile(
              icon: Icons.lock_open_rounded,
              label: 'Disarm Area',
              color: AppTheme.secondary,
              onTap: () {
                HapticFeedback.lightImpact();
                Navigator.pop(ctx);
                onAction(subsystem, 'disarm');
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _AreaOptionTile extends StatelessWidget {
  const _AreaOptionTile({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: BoxDecoration(
          color: AppTheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 18),
            ),
            const SizedBox(width: 16),
            Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 14,
                color: AppTheme.onSurface,
              ),
            ),
            const Spacer(),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppTheme.outlineVariant,
              size: 18,
            ),
          ],
        ),
      ),
    );
  }
}

class _CommandBanner extends StatelessWidget {
  const _CommandBanner({
    required this.message,
    required this.isError,
    required this.onDismiss,
  });
  final String message;
  final bool isError;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final bg = isError ? AppTheme.errorContainer : AppTheme.secondaryContainer;
    final fg = isError
        ? AppTheme.onErrorContainer
        : AppTheme.onSecondaryContainer;
    final isFault = message.toLowerCase().contains('closed');

    return Container(
      color: bg,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Icon(
            isError
                ? Icons.error_outline_rounded
                : Icons.check_circle_outline_rounded,
            color: fg,
            size: 18,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  message,
                  style: TextStyle(
                    color: fg,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (isFault)
                  TextButton(
                    onPressed: () => context.go('/devices'),
                    style: TextButton.styleFrom(
                      padding: EdgeInsets.zero,
                      minimumSize: const Size(0, 0),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: Text(
                      'Check sensors',
                      style: TextStyle(
                        fontFamily: AppTheme.fontFamily,
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        color: fg,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          IconButton(
            icon: Icon(Icons.close_rounded, size: 16, color: fg),
            onPressed: onDismiss,
          ),
        ],
      ),
    );
  }
}

class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: AppErrorState(
        title: 'Could not load site details',
        message: message,
        action: FilledButton(onPressed: onRetry, child: const Text('Retry')),
      ),
    );
  }
}

class _LockdownBanner extends StatefulWidget {
  const _LockdownBanner();

  @override
  State<_LockdownBanner> createState() => _LockdownBannerState();
}

class _LockdownBannerState extends State<_LockdownBanner>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _pulse;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _pulse = Tween<double>(
      begin: 0.7,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _pulse,
      builder: (context, child) => Opacity(
        opacity: _pulse.value,
        child: Container(
          width: double.infinity,
          color: Colors.orange.shade600,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          child: Row(
            children: [
              const Icon(
                Icons.lock_clock_rounded,
                color: Colors.white,
                size: 20,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'SERVICE SUSPENDED',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.2,
                      ),
                    ),
                    Text(
                      'Contact your dealer to restore monitoring.',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}



