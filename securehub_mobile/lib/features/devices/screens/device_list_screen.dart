import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/models/site_runtime_inventory.dart';
import '../../sites/providers/selected_site_provider.dart';
import '../../sites/providers/sites_provider.dart';
import '../../sites/providers/site_runtime_provider.dart';
import '../../../core/models/site.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/zone_utils.dart';
import '../../../shared/widgets/app_surfaces.dart';
import '../../../shared/widgets/shimmer_loading.dart';

class DeviceListScreen extends ConsumerStatefulWidget {
  const DeviceListScreen({super.key});

  @override
  ConsumerState<DeviceListScreen> createState() => _DeviceListScreenState();
}

class _DeviceListScreenState extends ConsumerState<DeviceListScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.indexIsChanging) {
        HapticFeedback.selectionClick();
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final siteId = ref.watch(currentSiteIdProvider);

    if (siteId == null) {
      return const Scaffold(
        backgroundColor: AppTheme.surface,
        body: Padding(
          padding: EdgeInsets.all(20),
          child: AppEmptyState(
            icon: Icons.business_rounded,
            title: 'No Active Site',
          ),
        ),
      );
    }

    final siteAsync = ref.watch(siteDetailProvider(siteId));
    final pollAsync = ref.watch(sitePollProvider(siteId));
    final runtimeAsync = ref.watch(siteRuntimeSnapshotProvider(siteId));

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: siteAsync.when(
          data: (site) {
            // Merge real-time poll data into the site object recursively
            final polledSubsystems = pollAsync.maybeWhen(
              data: (poll) => poll.subsystems,
              orElse: () => <Subsystem>[],
            );

            Subsystem mergeSubsystem(Subsystem s) {
              final polled = polledSubsystems.firstWhere(
                (p) =>
                    p.id == s.id ||
                    (p.subsystemNumber == s.subsystemNumber &&
                        s.subsystemNumber != 0),
                orElse: () => s,
              );

              // Critical: Merge zones to preserve structural data (names, zone/device numbers)
              // that might be missing in a "thin" poll response.
              final mergedZones = s.zones.map((z) {
                final polledZone = polled.zones.firstWhere(
                  (pz) =>
                      pz.id == z.id ||
                      (pz.zoneNumber == z.zoneNumber && z.zoneNumber != 0),
                  orElse: () => z,
                );

                if (polledZone == z) return z;

                return z.copyWith(
                  state: polledZone.state,
                  tamper: polledZone.tamper,
                  lowBattery: polledZone.lowBattery,
                  isOnline: polledZone.isOnline,
                  // Only take telemetry if it's not the default 0/empty
                  chargeValue:
                      (polledZone.chargeValue != null &&
                          polledZone.chargeValue != 0)
                      ? polledZone.chargeValue
                      : z.chargeValue,
                  signalStrength: polledZone.signalStrength.isNotEmpty
                      ? polledZone.signalStrength
                      : z.signalStrength,
                );
              }).toList();

              return s.copyWith(status: polled.status, zones: mergedZones);
            }

            final mergedSiteSubsystems = site.subsystems
                .map(mergeSubsystem)
                .toList();
            final mergedDevices = site.devices.map((d) {
              return d.copyWith(
                subsystems: d.subsystems.map(mergeSubsystem).toList(),
              );
            }).toList();

            final currentSite = site.copyWith(
              subsystems: mergedSiteSubsystems,
              devices: mergedDevices,
            );
            final runtime = runtimeAsync.valueOrNull;

            return Column(
              children: [
                // ── Tab Bar ──────────────────────────────────────────────
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 8,
                  ),
                  child: Container(
                    height: 48,
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceContainerLow,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: TabBar(
                      controller: _tabController,
                      indicatorSize: TabBarIndicatorSize.tab,
                      dividerColor: Colors.transparent,
                      indicator: BoxDecoration(
                        color: AppTheme.primary,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.primary.withValues(alpha: 0.3),
                            blurRadius: 8,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      labelColor: Colors.white,
                      unselectedLabelColor: AppTheme.onSurfaceVariant,
                      labelStyle: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                      unselectedLabelStyle: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                      tabs: const [
                        Tab(text: 'Sensors'),
                        Tab(text: 'Hubs & Modules'),
                      ],
                    ),
                  ),
                ),

                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _ZonesTab(site: currentSite),
                      _HardwareTab(site: currentSite, runtime: runtime),
                    ],
                  ),
                ),
              ],
            );
          },
          loading: () => const _LoadingSkeleton(),
          error: (err, _) => Padding(
            padding: const EdgeInsets.all(20),
            child: AppErrorState(
              title: 'Could not load devices',
              message: err.toString(),
            ),
          ),
        ),
    );
  }
}

class _ZonesTab extends StatelessWidget {
  const _ZonesTab({required this.site});
  final Site site;

  @override
  Widget build(BuildContext context) {
    final subsystemMap = <String, Subsystem>{};
    for (final subsystem in [
      ...site.subsystems,
      ...site.devices.expand((d) => d.subsystems),
    ]) {
      final key = subsystem.id.isNotEmpty
          ? subsystem.id
          : 'subsystem-${subsystem.subsystemNumber}';
      subsystemMap[key] = subsystem;
    }
    final allSubsystems = subsystemMap.values.toList();

    if (allSubsystems.isEmpty) {
      return Center(
        child: Text(
          'No zones configured',
          style: GoogleFonts.inter(color: AppTheme.onSurfaceVariant),
        ),
      );
    }

    return CustomScrollView(
      physics: const BouncingScrollPhysics(),
      slivers: [
        for (final sub in allSubsystems) ...[
          if (sub.zones.isNotEmpty) ...[
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                child: Row(
                  children: [
                    Text(
                      sub.name.toUpperCase(),
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.5,
                        color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Divider(
                        color: AppTheme.outlineVariant.withValues(alpha: 0.3),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, zoneIndex) => _ZoneTile(zone: sub.zones[zoneIndex]),
                  childCount: sub.zones.length,
                ),
              ),
            ),
          ],
        ],
        const SliverToBoxAdapter(child: SizedBox(height: 120)),
      ],
    );
  }
}

class _HardwareTab extends StatelessWidget {
  const _HardwareTab({required this.site, required this.runtime});
  final Site site;
  final SiteRuntimeSnapshot? runtime;

  @override
  Widget build(BuildContext context) {
    final devices = [...site.devices, ...site.videoDevices];
    final peripherals = [...(runtime?.peripherals ?? const <RuntimePeripheral>[])]
      ..sort((a, b) {
        final typeCompare = a.typeLabel.compareTo(b.typeLabel);
        if (typeCompare != 0) return typeCompare;
        return a.number.compareTo(b.number);
      });
    final outputs = [...(runtime?.outputs ?? const <RuntimeOutput>[])]
      ..sort((a, b) => a.number.compareTo(b.number));

    if (devices.isEmpty && peripherals.isEmpty && outputs.isEmpty) {
      return Center(
        child: Text(
          'No hardware synced yet',
          style: GoogleFonts.inter(color: AppTheme.onSurfaceVariant),
        ),
      );
    }

    return CustomScrollView(
      physics: const BouncingScrollPhysics(),
      slivers: [
        const SliverToBoxAdapter(child: SizedBox(height: 12)),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _StatChip(label: 'Hubs', value: devices.length),
                _StatChip(label: 'Controls', value: peripherals.length),
                _StatChip(label: 'Outputs', value: outputs.length),
                if ((runtime?.offlineDeviceCount ?? 0) > 0)
                  _StatChip(
                    label: 'Offline',
                    value: runtime?.offlineDeviceCount ?? 0,
                    color: AppTheme.error,
                  ),
              ],
            ),
          ),
        ),
        if (devices.isNotEmpty) ...[
          const SliverToBoxAdapter(
            child: _SectionHeading(title: 'HUBS & RECORDERS'),
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            sliver: SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, i) => _HubTile(device: devices[i]),
                childCount: devices.length,
              ),
            ),
          ),
        ],
        if (peripherals.isNotEmpty) ...[
          const SliverToBoxAdapter(
            child: _SectionHeading(title: 'CONTROLLERS & MODULES'),
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            sliver: SliverGrid(
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                mainAxisExtent: 130,
              ),
              delegate: SliverChildBuilderDelegate(
                (context, i) => _PeripheralTile(peripheral: peripherals[i]),
                childCount: peripherals.length,
              ),
            ),
          ),
        ],
        if (outputs.isNotEmpty) ...[
          const SliverToBoxAdapter(
            child: _SectionHeading(title: 'OUTPUTS'),
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            sliver: SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, i) => _OutputTile(output: outputs[i]),
                childCount: outputs.length,
              ),
            ),
          ),
        ],
        const SliverToBoxAdapter(child: SizedBox(height: 120)),
      ],
    );
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
      child: Text(
        title,
        style: GoogleFonts.inter(
          fontSize: 10,
          fontWeight: FontWeight.w900,
          letterSpacing: 1.5,
          color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
        ),
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.label,
    required this.value,
    this.color = AppTheme.primary,
  });

  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$value',
            style: GoogleFonts.inter(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppTheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _HubTile extends StatelessWidget {
  const _HubTile({required this.device});

  final Object device;

  @override
  Widget build(BuildContext context) {
    String name = '';
    bool isOnline = false;
    String serialNumber = '';
    String modelNumber = '';
    bool isPanel = false;

    if (device is AlarmPanelDevice) {
      final panel = device as AlarmPanelDevice;
      isPanel = true;
      name = panel.name.isEmpty ? 'Security Hub' : panel.name;
      isOnline = panel.isOnline;
      serialNumber = panel.serialNumber.isEmpty ? panel.hikDeviceId : panel.serialNumber;
      modelNumber = panel.modelNumber;
    } else if (device is VideoDevice) {
      final video = device as VideoDevice;
      name = video.name.isEmpty ? 'NVR / Camera Hub' : video.name;
      isOnline = video.isOnline;
      serialNumber = video.serialNumber.isEmpty ? video.hikDeviceId : video.serialNumber;
      modelNumber = video.modelNumber;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: AppTheme.outlineVariant.withValues(alpha: 0.2),
        ),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 56,
            height: 56,
            child: Image.asset(
              isPanel ? 'assets/devices/axpro.png' : 'assets/devices/nvr.png',
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                    color: AppTheme.primary,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: isOnline ? AppTheme.secondary : AppTheme.error,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      isOnline ? 'Online' : 'Offline',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: isOnline
                            ? AppTheme.secondary
                            : AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '•',
                      style: TextStyle(
                        color: AppTheme.onSurfaceVariant.withValues(alpha: 0.3),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        modelNumber.isNotEmpty ? modelNumber : serialNumber,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PeripheralTile extends StatelessWidget {
  const _PeripheralTile({required this.peripheral});

  final RuntimePeripheral peripheral;

  @override
  Widget build(BuildContext context) {
    final deviceImage = ZoneUtils.getDeviceImage(peripheral.type, peripheral.name);
    final badgeColor = peripheral.isOnline ? AppTheme.secondary : AppTheme.error;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: AppTheme.outlineVariant.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(
                width: 34,
                height: 34,
                child: Image.asset(deviceImage, fit: BoxFit.contain),
              ),
              const Spacer(),
              _StatusBadge(
                state: peripheral.statusLabel,
                color: badgeColor,
                mini: true,
              ),
            ],
          ),
          const Spacer(),
          Text(
            peripheral.name.isEmpty ? peripheral.typeLabel : peripheral.name,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: GoogleFonts.inter(
              fontWeight: FontWeight.w700,
              fontSize: 13,
              color: AppTheme.primary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            peripheral.number > 0
                ? '${peripheral.typeLabel} ${peripheral.number}'
                : peripheral.typeLabel,
            style: GoogleFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: AppTheme.onSurfaceVariant.withValues(alpha: 0.7),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  peripheral.batteryStatus.isEmpty
                      ? 'Battery --'
                      : 'Battery ${ZoneUtils.formatDeviceTypeLabel(peripheral.batteryStatus, fallback: '--')}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    color: AppTheme.onSurfaceVariant.withValues(alpha: 0.7),
                  ),
                ),
              ),
              _SignalIndicator(strength: peripheral.signalStrength, mini: true),
            ],
          ),
        ],
      ),
    );
  }
}

class _OutputTile extends StatelessWidget {
  const _OutputTile({required this.output});

  final RuntimeOutput output;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: AppTheme.outlineVariant.withValues(alpha: 0.2),
        ),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 46,
            height: 46,
            child: Image.asset(
              ZoneUtils.getDeviceImage('output_module', output.name),
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  output.name.isEmpty ? 'Output ${output.number}' : output.name,
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    color: AppTheme.primary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  output.number > 0
                      ? 'Output ${output.number}'
                      : 'Alarm Output',
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.onSurfaceVariant.withValues(alpha: 0.7),
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    _StatusBadge(
                      state: output.statusLabel,
                      color: output.isOnline ? AppTheme.secondary : AppTheme.error,
                      mini: true,
                    ),
                    const SizedBox(width: 12),
                    _SignalIndicator(strength: output.signalStrength, mini: true),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ZoneTile extends ConsumerWidget {
  const _ZoneTile({required this.zone});
  final Zone zone;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusColor = ZoneUtils.getStatusColor(
      zone.state,
      tamper: zone.tamper,
      isOnline: zone.isOnline,
    );
    final deviceImage = ZoneUtils.getDeviceImage(zone.detectorType, zone.name);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: AppTheme.outlineVariant.withValues(alpha: 0.2),
        ),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 52,
            height: 52,
            child: Image.asset(deviceImage, fit: BoxFit.contain),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        zone.name,
                        style: GoogleFonts.inter(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                          color: AppTheme.primary,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ),
                    _StatusBadge(state: zone.state, color: statusColor, mini: true),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Text(
                      'Zone ${zone.zoneNumber}',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.onSurfaceVariant.withValues(alpha: 0.6),
                      ),
                    ),
                    const Spacer(),
                    if (zone.lowBattery || (zone.chargeValue != null && zone.chargeValue! <= 20))
                      Icon(Icons.battery_alert_rounded, size: 14, color: AppTheme.error.withValues(alpha: 0.8))
                    else if (zone.chargeValue != null)
                      _MiniBadge(
                        label: '${zone.chargeValue}%',
                        color: AppTheme.secondary,
                        icon: Icons.battery_std_rounded,
                      ),
                    const SizedBox(width: 12),
                    _SignalIndicator(strength: zone.signalStrength, mini: true),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.state, required this.color, this.mini = false});
  final String state;
  final Color color;
  final bool mini;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: mini ? 6 : 10,
        vertical: mini ? 2 : 3,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(mini ? 4 : 6),
      ),
      child: Text(
        state.toUpperCase(),
        style: GoogleFonts.inter(
          fontSize: mini ? 8 : 10,
          fontWeight: FontWeight.w900,
          letterSpacing: 0.5,
          color: color,
        ),
      ),
    );
  }
}

class _MiniBadge extends StatelessWidget {
  const _MiniBadge({
    required this.label,
    required this.color,
    required this.icon,
  });
  final String label;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      ],
    );
  }
}

class _SignalIndicator extends StatelessWidget {
  const _SignalIndicator({required this.strength, this.mini = false});
  final String strength;
  final bool mini;

  @override
  Widget build(BuildContext context) {
    int bars = 0;
    final s = strength.toLowerCase();
    if (s == 'strong' || s == 'excellent') {
      bars = 4;
    } else if (s == 'good' || s == 'ok') {
      bars = 3;
    } else if (s == 'medium' || s == 'fair') {
      bars = 2;
    } else if (s == 'weak' || s == 'poor') {
      bars = 1;
    } else if (s == 'none' || s == 'disconnected' || s == 'lost') {
      bars = 0;
    }

    final isLost = bars == 0 && strength.isNotEmpty;
    final color = isLost
        ? AppTheme.onSurfaceVariant.withValues(alpha: 0.4)
        : AppTheme.secondary;

    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: List.generate(4, (i) {
            return Container(
              width: 2.5,
              height: 3.0 + (i * 2.5),
              margin: const EdgeInsets.symmetric(horizontal: 0.5),
              decoration: BoxDecoration(
                color: i < bars ? color : AppTheme.outlineVariant.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(1),
              ),
            );
          }),
        ),
        if (!mini) ...[
          const SizedBox(width: 8),
          Text(
            strength.isEmpty ? 'N/A' : strength.toUpperCase(),
            style: GoogleFonts.inter(
              fontSize: 8,
              fontWeight: FontWeight.w700,
              color: isLost
                  ? AppTheme.onSurfaceVariant.withValues(alpha: 0.4)
                  : AppTheme.onSurfaceVariant,
            ),
          ),
        ],
      ],
    );
  }
}

class _LoadingSkeleton extends StatelessWidget {
  const _LoadingSkeleton();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
          child: ShimmerLoading(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(width: 180, height: 28, color: Colors.white),
                const SizedBox(height: 8),
                Container(width: 220, height: 14, color: Colors.white),
              ],
            ),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            itemCount: 5,
            itemBuilder: (context, index) => const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: ZoneTileShimmer(),
            ),
          ),
        ),
      ],
    );
  }
}

class ZoneTileShimmer extends StatelessWidget {
  const ZoneTileShimmer({super.key});

  @override
  Widget build(BuildContext context) {
    return ShimmerLoading(
      child: Container(
        height: 80,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
        ),
      ),
    );
  }
}
