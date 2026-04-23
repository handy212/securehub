import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:securehub_mobile/core/utils/zone_utils.dart';

import '../../../core/api/exceptions.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../../alarms/providers/alarm_control_provider.dart';
import '../providers/sites_provider.dart';
import '../widgets/subsystem_card.dart';
import 'package:sliver_tools/sliver_tools.dart';
import '../widgets/zone_health_badge.dart';
import '../../../shared/widgets/app_surfaces.dart';
import '../../../shared/widgets/shimmer_loading.dart';

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
  void initState() {
    super.initState();
  }

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

    // Deduplicate and merge subsystems from Site and SitePoll
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

    // Auto-scroll to cameras if requested via query param
    final verifyParam = GoRouterState.of(context).uri.queryParameters['verify'];
    if (verifyParam == 'true') {
      WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToCameras());
    }

    final isArmedAway = allSubsystems.any((s) => s.status == 'armed');
    final isArmedStay = allSubsystems.any((s) => s.status == 'stay');
    final hasAlarm = (poll?.activeAlarmCount ?? 0) > 0;
    final isArmed = isArmedAway || isArmedStay;
    final openZones = allSubsystems.expand((subsystem) => subsystem.zones).where(
      (zone) => zone.state.toLowerCase() == 'open',
    ).toList();
    final hasOpenZone = openZones.isNotEmpty;
    final openZoneSummary = openZones.take(3).map((zone) => zone.name).join(', ');
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
      backgroundColor:
          Colors.transparent, // Let MainScaffold backdrop show through
      body: CustomScrollView(
        controller: _scrollController,
        physics: const BouncingScrollPhysics(),
        slivers: [
          // ── Header Section ──────────────────────────────────────────────
          // ── Command feedback banner ───────────────────────────────────────
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

          // ── Status Hero Section ──────────────────────────────────────────
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
                  // Status card
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
                        _StatusHero(
                          isArmed: isArmed,
                          hasAlarm: hasAlarm,
                          isSuspended: isSuspended,
                          tone: readinessTone,
                          compact: isCompactHeight,
                        ),
                        SizedBox(height: isCompactHeight ? 14 : 20),
                        Text(
                          statusTitle,
                          style: GoogleFonts.inter(
                            fontSize: statusTitleSize,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.primary,
                          ),
                        ),
                        SizedBox(height: isCompactHeight ? 4 : 6),
                        Text(
                          statusSubtitle,
                          textAlign: TextAlign.center,
                          style: GoogleFonts.inter(
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

                  // Arm/Disarm bento grid
                  if (!isSuspended) ...[
                    Row(
                      children: [
                        Expanded(
                          child: _BentoActionButton(
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
                          child: _BentoActionButton(
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
                      child: _BentoActionButton(
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
                  _CameraPreviewSection(
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
                        style: GoogleFonts.inter(
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

          // ── Areas section ────────────────────────────────────────────────
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
                // _SliverZoneList(
                //   allSubsystems: allSubsystems,
                //   onCameraVerify: _scrollToCameras,
                // ),
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
          title: Text(
            'Open Zones',
            style: GoogleFonts.abel(
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
                                      style: GoogleFonts.inter(
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
              style: FilledButton.styleFrom(
                backgroundColor: AppTheme.primary,
              ),
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
    // Provide tactile feedback on action
    HapticFeedback.mediumImpact();

    await ref
        .read(alarmControlNotifierProvider.notifier)
        .sendBulkCommand(
          siteId: siteId,
          subsystemIds: subsystemIds,
          action: action,
        );
  }
}

// ── Status Hero Widget ────────────────────────────────────────────────────────

class _StatusHero extends StatefulWidget {
  const _StatusHero({
    required this.isArmed,
    required this.hasAlarm,
    required this.isSuspended,
    required this.tone,
    this.compact = false,
  });
  final bool isArmed;
  final bool hasAlarm;
  final bool isSuspended;
  final Color tone;
  final bool compact;

  @override
  State<_StatusHero> createState() => _StatusHeroState();
}

class _StatusHeroState extends State<_StatusHero>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _animation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Color glowColor = widget.tone;
    final outerSize = widget.compact ? 138.0 : 180.0;
    final ringSize = widget.compact ? 114.0 : 150.0;
    final coreSize = widget.compact ? 88.0 : 120.0;
    final logoPadding = widget.compact ? 16.0 : 22.0;
    final badgeSize = widget.compact ? 20.0 : 24.0;
    final badgeInset = widget.compact ? 8.0 : 12.0;
    final badgeIconSize = widget.compact ? 10.0 : 12.0;

    final IconData statusIcon = widget.isSuspended
        ? Icons.lock_clock_rounded
        : (widget.hasAlarm
              ? Icons.priority_high_rounded
              : (widget.isArmed
                    ? Icons.shield_rounded
                    : Icons.shield_outlined));

    return Stack(
      alignment: Alignment.center,
      children: [
        AnimatedBuilder(
          animation: _animation,
          builder: (context, child) {
            return Container(
              width: outerSize,
              height: outerSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: glowColor.withValues(alpha: 0.15 * _animation.value),
                    blurRadius: (widget.compact ? 28 : 40) +
                        ((widget.compact ? 12 : 20) * _animation.value),
                    spreadRadius: (widget.compact ? 6 : 10) +
                        ((widget.compact ? 6 : 10) * _animation.value),
                  ),
                ],
              ),
            );
          },
        ),
        Container(
          width: ringSize,
          height: ringSize,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: glowColor.withValues(alpha: 0.1),
              width: 1,
            ),
          ),
        ),
        Container(
          width: coreSize,
          height: coreSize,
          decoration: BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: ClipOval(
            child: Stack(
              children: [
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(logoPadding),
                    child: Image.asset(
                      'assets/images/Logo-WhiteBG.png',
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
                Positioned(
                  bottom: badgeInset,
                  right: badgeInset,
                  child: Container(
                    width: badgeSize,
                    height: badgeSize,
                    decoration: BoxDecoration(
                      color: glowColor,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Colors.white,
                        width: widget.compact ? 2 : 3,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: glowColor.withValues(alpha: 0.4),
                          blurRadius: 8,
                        ),
                      ],
                    ),
                    child: Icon(
                      statusIcon,
                      color: Colors.white,
                      size: badgeIconSize,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// ── Bento Action Button ────────────────────────────────────────────────────────

class _AreasSectionHeader extends StatelessWidget {
  const _AreasSectionHeader({this.count});

  final int? count;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Text(
              'Areas',
              style: GoogleFonts.inter(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.6,
                color: AppTheme.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BentoActionButton extends StatefulWidget {
  const _BentoActionButton({
    required this.icon,
    required this.label,
    required this.isPrimary,
    required this.onTap,
    this.isActive = false,
    this.isFullWidth = false,
    this.compact = false,
  });
  final IconData icon;
  final String label;
  final bool isPrimary;
  final bool isActive;
  final bool isFullWidth;
  final bool compact;
  final VoidCallback? onTap;

  @override
  State<_BentoActionButton> createState() => _BentoActionButtonState();
}

class _BentoActionButtonState extends State<_BentoActionButton> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final bool useBrandColor = widget.isActive;
    final bool isDisarm = widget.label.toLowerCase().contains('disarm');

    final Color activeBg = isDisarm ? AppTheme.secondary : AppTheme.primary;
    Color activeFg = Colors.white;
    final buttonHeight = widget.isFullWidth
        ? (widget.compact ? 54.0 : 64.0)
        : (widget.compact ? 96.0 : 120.0);
    final buttonPadding = widget.compact ? 16.0 : 20.0;
    final iconSize = widget.isFullWidth
        ? (widget.compact ? 20.0 : 22.0)
        : (widget.compact ? 24.0 : 28.0);
    final labelSize = widget.compact ? 13.0 : 15.0;

    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      onTap: widget.onTap,
      child: AnimatedScale(
        scale: _isPressed ? 0.96 : 1.0,
        duration: const Duration(milliseconds: 100),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          height: buttonHeight,
          padding: EdgeInsets.all(buttonPadding),
          decoration: BoxDecoration(
            gradient: useBrandColor
                ? LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [activeBg, activeBg.withValues(alpha: 0.8)],
                  )
                : (widget.isPrimary
                      ? const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [AppTheme.primary, AppTheme.primaryContainer],
                        )
                      : null),
            color: (useBrandColor || widget.isPrimary)
                ? null
                : AppTheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(20),
            boxShadow: _isPressed ? [] : AppTheme.cardShadow,
            border: Border.all(
              color: useBrandColor
                  ? activeBg.withValues(alpha: 0.2)
                  : (widget.isPrimary
                        ? Colors.transparent
                        : AppTheme.outlineVariant.withValues(alpha: 0.1)),
              width: 1,
            ),
          ),
          child: widget.isFullWidth
              ? Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      widget.icon,
                      color: (useBrandColor || widget.isPrimary)
                          ? activeFg
                          : AppTheme.secondary,
                      size: iconSize,
                    ),
                    SizedBox(width: widget.compact ? 8 : 12),
                    Text(
                      widget.label,
                      style: GoogleFonts.inter(
                        fontWeight: FontWeight.w700,
                        fontSize: labelSize,
                        color: (useBrandColor || widget.isPrimary)
                            ? activeFg
                            : AppTheme.onSurface,
                      ),
                    ),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Icon(
                      widget.icon,
                      color: (useBrandColor || widget.isPrimary)
                          ? activeFg
                          : AppTheme.secondary,
                      size: iconSize,
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.label,
                          style: GoogleFonts.inter(
                            fontWeight: FontWeight.w700,
                            fontSize: labelSize,
                            color: (useBrandColor || widget.isPrimary)
                                ? activeFg
                                : AppTheme.onSurface,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),

// ── Sliver Site Body ──────────────────────────────────────────────────────────

        ),
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
    final screenWidth = MediaQuery.sizeOf(context).width;
    final crossAxisCount = screenWidth < 390 ? 1 : 2;
    final childAspectRatio = screenWidth < 390 ? 2.9 : 2.2;

    if (allSubsystems.isEmpty) {
      return const SliverToBoxAdapter(
        child: Padding(
          padding: EdgeInsets.all(20),
          child: Text('No subsystems found.'),
        ),
      );
    }

    return SliverPadding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
      sliver: SliverGrid(
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: crossAxisCount,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: childAspectRatio,
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
              style: GoogleFonts.inter(
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
              style: GoogleFonts.inter(
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
              style: GoogleFonts.inter(
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

// ── Zone List ─────────────────────────────────────────────────────────────────

// ignore: unused_element
class _SliverZoneList extends StatelessWidget {
  const _SliverZoneList({
    required this.allSubsystems,
    required this.onCameraVerify,
  });
  final List<Subsystem> allSubsystems;
  final VoidCallback onCameraVerify;

  @override
  Widget build(BuildContext context) {
    return MultiSliver(
      children: [
        for (final sub in allSubsystems) ...[
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Text(
                sub.name.toUpperCase(),
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                  color: AppTheme.onSurfaceVariant,
                ),
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            sliver: SliverList(
              delegate: SliverChildBuilderDelegate((context, i) {
                final zone = sub.zones[i];
                final isMotion =
                    zone.name.toLowerCase().contains('motion') ||
                    zone.name.toLowerCase().contains('pir');

                return _ZoneTile(
                  zone: zone,
                  subsystemName: sub.name,
                  onCameraLink: isMotion ? onCameraVerify : null,
                );
              }, childCount: sub.zones.length),
            ),
          ),
        ],
      ],
    );
  }
}

class _ZoneTile extends StatelessWidget {
  const _ZoneTile({
    required this.zone,
    required this.subsystemName,
    this.onCameraLink,
  });
  final Zone zone;
  final String subsystemName;
  final VoidCallback? onCameraLink;

  @override
  Widget build(BuildContext context) {
    final isAlarm = zone.state == 'alarm' || zone.tamper;
    final isOpen = zone.state == 'open' && !zone.tamper;

    final Color barColor = isAlarm
        ? AppTheme.error
        : (isOpen ? AppTheme.onTertiaryContainer : AppTheme.secondary);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          // 4px tonal bar accent
          Container(
            width: 4,
            height: 72,
            decoration: BoxDecoration(
              color: barColor,
              borderRadius: const BorderRadius.horizontal(
                left: Radius.circular(16),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Container(
            width: 44,
            height: 44,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.onSurface.withValues(alpha: 0.05),
              shape: BoxShape.circle,
            ),
            child: Image.asset(
              ZoneUtils.getDeviceImage(zone.detectorType, zone.name),
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  zone.name,
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                    color: AppTheme.primary,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: isAlarm
                            ? AppTheme.errorContainer
                            : (isOpen
                                  ? AppTheme.tertiaryFixed
                                  : AppTheme.secondaryContainer),
                        borderRadius: BorderRadius.circular(100),
                      ),
                      child: Text(
                        zone.state.toUpperCase(),
                        style: GoogleFonts.inter(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                          color: isAlarm
                              ? AppTheme.onErrorContainer
                              : (isOpen
                                    ? AppTheme.onTertiaryContainer
                                    : AppTheme.onSecondaryContainer),
                        ),
                      ),
                    ),
                    if (onCameraLink != null) ...[
                      const SizedBox(width: 8),
                      Text(
                        'Camera available',
                        style: GoogleFonts.inter(
                          fontSize: 10,
                          color: AppTheme.onSurfaceVariant,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
          if (onCameraLink != null)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: IconButton(
                onPressed: () {
                  HapticFeedback.lightImpact();
                  onCameraLink?.call();
                },
                icon: const Icon(
                  Icons.videocam_rounded,
                  size: 20,
                  color: AppTheme.primary,
                ),
                tooltip: 'Verify with Camera',
              ),
            )
          else
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    zone.lowBattery
                        ? Icons.battery_alert_rounded
                        : Icons.battery_full_rounded,
                    size: 16,
                    color: zone.lowBattery
                        ? AppTheme.error
                        : AppTheme.onSurfaceVariant,
                  ),
                  const SizedBox(height: 4),
                  ZoneHealthBadge(zone: zone),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

// ── Command Banner ────────────────────────────────────────────────────────────

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
                  style: GoogleFonts.inter(
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
                      style: GoogleFonts.inter(
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

// ── Error Body ────────────────────────────────────────────────────────────────

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

// ── Lockdown Banner ───────────────────────────────────────────────────────────

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
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.2,
                      ),
                    ),
                    Text(
                      'Contact your dealer to restore monitoring.',
                      style: GoogleFonts.inter(
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
// ── Camera Section ────────────────────────────────────────────────────────────

class _CameraPreviewSection extends StatelessWidget {
  const _CameraPreviewSection({
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
            style: GoogleFonts.inter(
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
                      style: GoogleFonts.inter(
                        color: Colors.white.withValues(alpha: 0.4),
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2.0,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'RECONNECTING...',
                      style: GoogleFonts.inter(
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
                  color: channel.isOnline
                      ? AppTheme.error
                      : Colors.grey.shade800,
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
                      style: GoogleFonts.inter(
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
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  if (channel.isOnline)
                    Text(
                      'Tap to open live view',
                      style: GoogleFonts.inter(
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
